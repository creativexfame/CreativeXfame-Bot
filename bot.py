import os
import csv
import io
from datetime import datetime, timedelta

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

import database


# =========================================================
# ENVIRONMENT
# =========================================================

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID", "0"))
ADMIN_ROLE_ID = int(os.getenv("ADMIN_ROLE_ID", "0"))


# =========================================================
# INTENTS
# =========================================================

intents = discord.Intents.default()


# =========================================================
# BOT
# =========================================================

class CreativeXfameBot(commands.Bot):

    def __init__(self):

        super().__init__(
            command_prefix="!",
            intents=intents
        )

    async def setup_hook(self):

        database.setup_database()

        guild = discord.Object(
            id=GUILD_ID
        )

        self.tree.copy_global_to(
            guild=guild
        )

        await self.tree.sync(
            guild=guild
        )

        print("✅ Slash commands synced!")


bot = CreativeXfameBot()


# =========================================================
# READY
# =========================================================

@bot.event
async def on_ready():

    print(f"✅ Logged in as {bot.user}")
    print("🚀 CreativeXfame Bot is ONLINE!")


# =========================================================
# ADMIN CHECK
# =========================================================

def is_admin(interaction: discord.Interaction):

    if not interaction.guild:
        return False

    if ADMIN_ROLE_ID == 0:
        return False

    return any(
        role.id == ADMIN_ROLE_ID
        for role in interaction.user.roles
    )


# =========================================================
# WEEK
# =========================================================

def get_week_dates():

    today = datetime.now().date()

    monday = today - timedelta(
        days=today.weekday()
    )

    sunday = monday + timedelta(
        days=6
    )

    return monday, sunday


# =========================================================
# PORTAL EMBED
# =========================================================

def create_portal_embed():

    is_open = database.are_submissions_open()

    monday, sunday = get_week_dates()

    if is_open:

        status_text = "🟢 OPEN"

        description = (
            "Submissions are currently being accepted."
        )

    else:

        status_text = "🔴 CLOSED"

        description = (
            "Submissions are currently closed."
        )

    embed = discord.Embed(
        title="🎬 CreativeXfame Submission Portal",
        description=description,
        color=(
            discord.Color.green()
            if is_open
            else discord.Color.red()
        )
    )

    embed.add_field(
        name="📊 Portal Status",
        value=status_text,
        inline=False
    )

    embed.add_field(
        name="📅 Current Submission Week",
        value=(
            f"**{monday.strftime('%d %b %Y')}**"
            f" → "
            f"**{sunday.strftime('%d %b %Y')}**"
        ),
        inline=False
    )

    embed.add_field(
        name="📝 Submission Status",
        value=(
            "✅ ACCEPTING SUBMISSIONS"
            if is_open
            else
            "❌ NOT ACCEPTING SUBMISSIONS"
        ),
        inline=False
    )

    embed.set_footer(
        text="Only administrators can change portal status."
    )

    return embed


# =========================================================
# PORTAL CONTROL VIEW
# =========================================================

class PortalControlView(discord.ui.View):

    def __init__(self):

        super().__init__(
            timeout=300
        )


    @discord.ui.button(
        label="Open Portal",
        emoji="🔓",
        style=discord.ButtonStyle.success
    )
    async def open_portal(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        if not is_admin(interaction):

            await interaction.response.send_message(
                "❌ You don't have permission.",
                ephemeral=True
            )

            return

        try:

            database.set_submissions_status(True)

            await interaction.response.edit_message(
                embed=create_portal_embed(),
                view=self
            )

        except Exception as error:

            await interaction.response.send_message(
                f"❌ Database error:\n`{str(error)[:1000]}`",
                ephemeral=True
            )


    @discord.ui.button(
        label="Close Portal",
        emoji="🔒",
        style=discord.ButtonStyle.danger
    )
    async def close_portal(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        if not is_admin(interaction):

            await interaction.response.send_message(
                "❌ You don't have permission.",
                ephemeral=True
            )

            return

        try:

            database.set_submissions_status(False)

            await interaction.response.edit_message(
                embed=create_portal_embed(),
                view=self
            )

        except Exception as error:

            await interaction.response.send_message(
                f"❌ Database error:\n`{str(error)[:1000]}`",
                ephemeral=True
            )


    @discord.ui.button(
        label="Refresh",
        emoji="🔄",
        style=discord.ButtonStyle.secondary
    )
    async def refresh_portal(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        if not is_admin(interaction):

            await interaction.response.send_message(
                "❌ You don't have permission.",
                ephemeral=True
            )

            return

        await interaction.response.edit_message(
            embed=create_portal_embed(),
            view=self
        )


# =========================================================
# /PORTAL
# =========================================================

@bot.tree.command(
    name="portal",
    description="Open submission portal control panel"
)
async def portal(
    interaction: discord.Interaction
):

    if not is_admin(interaction):

        await interaction.response.send_message(
            "❌ You don't have permission.",
            ephemeral=True
        )

        return

    await interaction.response.send_message(
        embed=create_portal_embed(),
        view=PortalControlView(),
        ephemeral=True
    )


# =========================================================
# ACCOUNT MODAL
# =========================================================

class AccountModal(
    discord.ui.Modal,
    title="Add Social Media Account"
):

    username = discord.ui.TextInput(
        label="Account Username",
        placeholder="@yourusername",
        required=True,
        max_length=100
    )

    def __init__(self, platform):

        super().__init__()

        self.platform = platform


    async def on_submit(
        self,
        interaction: discord.Interaction
    ):

        username = self.username.value.strip()
        username = username.replace(" ", "")
        username = username.lstrip("@")

        if not username:

            await interaction.response.send_message(
                "❌ Please enter a valid username.",
                ephemeral=True
            )

            return

        username = "@" + username

        try:

            account_id = database.add_account(
                discord_id=str(interaction.user.id),
                discord_username=str(interaction.user),
                platform=self.platform,
                username=username
            )

        except Exception as error:

            await interaction.response.send_message(
                f"❌ Database error:\n`{str(error)[:1000]}`",
                ephemeral=True
            )

            return

        await interaction.response.send_message(
            f"""
✅ **Account Added Successfully!**

**Account ID:** #{account_id}
**Platform:** {self.platform}
**Account:** {username}

You can add another account anytime.
""",
            ephemeral=True
        )


# =========================================================
# PLATFORM SELECT
# =========================================================

class PlatformSelect(discord.ui.Select):

    def __init__(self):

        options = [

            discord.SelectOption(
                label="TikTok",
                emoji="🎵",
                description="Add a TikTok account"
            ),

            discord.SelectOption(
                label="Instagram",
                emoji="📸",
                description="Add an Instagram account"
            ),

            discord.SelectOption(
                label="YouTube",
                emoji="▶️",
                description="Add a YouTube account"
            ),

            discord.SelectOption(
                label="Facebook",
                emoji="📘",
                description="Add a Facebook account"
            ),

            discord.SelectOption(
                label="Snapchat",
                emoji="👻",
                description="Add a Snapchat account"
            )

        ]

        super().__init__(
            placeholder="Select your platform...",
            options=options
        )


    async def callback(
        self,
        interaction: discord.Interaction
    ):

        await interaction.response.send_modal(
            AccountModal(self.values[0])
        )


# =========================================================
# PLATFORM VIEW
# =========================================================

class PlatformView(discord.ui.View):

    def __init__(self):

        super().__init__(
            timeout=120
        )

        self.add_item(
            PlatformSelect()
        )


# =========================================================
# /ADD_ACCOUNT
# =========================================================

@bot.tree.command(
    name="add_account",
    description="Add a social media account"
)
async def add_account(
    interaction: discord.Interaction
):

    await interaction.response.send_message(
        "### 📱 Add Your Social Media Account\n\n"
        "Select the platform you want to add.\n\n"
        "✅ Multiple accounts per platform are allowed.",
        view=PlatformView(),
        ephemeral=True
    )


# =========================================================
# /MY_ACCOUNTS
# =========================================================

@bot.tree.command(
    name="my_accounts",
    description="View your registered accounts"
)
async def my_accounts(
    interaction: discord.Interaction
):

    try:

        accounts = database.get_user_accounts(
            str(interaction.user.id)
        )

    except Exception as error:

        await interaction.response.send_message(
            f"❌ Database error:\n`{str(error)[:1000]}`",
            ephemeral=True
        )

        return

    if not accounts:

        await interaction.response.send_message(
            "❌ You don't have any registered accounts yet.\n\n"
            "Use `/add_account`.",
            ephemeral=True
        )

        return

    embed = discord.Embed(
        title="📋 My Social Media Accounts",
        color=discord.Color.blurple()
    )

    grouped = {}

    for account in accounts:

        account_id, platform, username, created_at = account

        grouped.setdefault(
            platform,
            []
        ).append(
            (account_id, username)
        )

    for platform, platform_accounts in grouped.items():

        lines = []

        for account_id, username in platform_accounts:

            lines.append(
                f"**#{account_id}** — {username}"
            )

        embed.add_field(
            name=f"{platform} ({len(platform_accounts)} accounts)",
            value="\n".join(lines),
            inline=False
        )

    await interaction.response.send_message(
        embed=embed,
        ephemeral=True
    )


# =========================================================
# /REMOVE_ACCOUNT
# =========================================================

@bot.tree.command(
    name="remove_account",
    description="Remove your social media account"
)
@app_commands.describe(
    account_id="Account ID shown in /my_accounts"
)
async def remove_account(
    interaction: discord.Interaction,
    account_id: int
):

    try:

        deleted = database.delete_account(
            account_id,
            str(interaction.user.id)
        )

    except Exception as error:

        await interaction.response.send_message(
            f"❌ Database error:\n`{str(error)[:1000]}`",
            ephemeral=True
        )

        return

    if deleted:

        await interaction.response.send_message(
            f"✅ Account **#{account_id}** removed successfully.",
            ephemeral=True
        )

    else:

        await interaction.response.send_message(
            "❌ Account not found.",
            ephemeral=True
        )


# =========================================================
# /ALL_ACCOUNTS
# =========================================================

@bot.tree.command(
    name="all_accounts",
    description="View all registered accounts"
)
async def all_accounts(
    interaction: discord.Interaction
):

    if not is_admin(interaction):

        await interaction.response.send_message(
            "❌ You don't have permission.",
            ephemeral=True
        )

        return

    try:

        accounts = database.get_all_accounts()

    except Exception as error:

        await interaction.response.send_message(
            f"❌ Database error:\n`{str(error)[:1000]}`",
            ephemeral=True
        )

        return

    if not accounts:

        await interaction.response.send_message(
            "📭 No accounts registered yet.",
            ephemeral=True
        )

        return

    output = io.StringIO()

    for account in accounts:

        (
            account_id,
            discord_id,
            discord_username,
            platform,
            username,
            created_at
        ) = account

        output.write(
            f"#{account_id} | "
            f"{discord_username} | "
            f"{platform} | "
            f"{username}\n"
        )

    text = output.getvalue()

    if len(text) > 1800:

        text = text[:1800] + "\n..."

    await interaction.response.send_message(
        f"📋 **All Accounts: {len(accounts)}**\n\n"
        f"```text\n{text}\n```",
        ephemeral=True
    )


# =========================================================
# /EXPORT_ACCOUNTS
# =========================================================

@bot.tree.command(
    name="export_accounts",
    description="Export all accounts to CSV"
)
async def export_accounts(
    interaction: discord.Interaction
):

    if not is_admin(interaction):

        await interaction.response.send_message(
            "❌ You don't have permission.",
            ephemeral=True
        )

        return

    try:

        accounts = database.get_all_accounts()

        output = io.StringIO()

        writer = csv.writer(output)

        writer.writerow([
            "Account ID",
            "Discord ID",
            "Discord Username",
            "Platform",
            "Username",
            "Created At"
        ])

        for account in accounts:

            writer.writerow(account)

        data = io.BytesIO(
            output.getvalue().encode("utf-8-sig")
        )

        file = discord.File(
            data,
            filename="CreativeXfame_accounts.csv"
        )

        await interaction.response.send_message(
            "📊 **Accounts exported successfully!**",
            file=file,
            ephemeral=True
        )

    except Exception as error:

        await interaction.response.send_message(
            f"❌ Export failed:\n`{str(error)[:1000]}`",
            ephemeral=True
        )


# =========================================================
# SUBMISSION EMBED
# =========================================================

def create_submission_embed(submission):

    embed = discord.Embed(
        title=f"📥 Submission #{submission['id']}",
        color=discord.Color.orange()
    )

    embed.add_field(
        name="👤 Clipper",
        value=(
            f"{submission['discord_username']}\n"
            f"Whop: **{submission['whop_username']}**"
        ),
        inline=False
    )

    embed.add_field(
        name="👀 Total Views",
        value=f"**{submission['total_views']:,}**",
        inline=True
    )

    embed.add_field(
        name="📊 Status",
        value=f"**{submission['status']}**",
        inline=True
    )

    embed.add_field(
        name="🔗 Google Drive",
        value=f"[Open Submission]({submission['google_drive_link']})",
        inline=False
    )

    account_lines = []

    for account in submission["accounts"]:

        account_id, platform, username, views = account

        account_lines.append(
            f"**{platform}** — {username} → "
            f"**{views:,} views**"
        )

    if account_lines:

        embed.add_field(
            name="📱 Accounts",
            value="\n".join(account_lines),
            inline=False
        )

    embed.add_field(
        name="📅 Submitted",
        value=submission["created_at"][:19],
        inline=False
    )

    if submission.get("payout"):

        embed.add_field(
            name="💰 Payout",
            value=f"**{submission['payout']}**",
            inline=True
        )

    return embed


# =========================================================
# PAYOUT MODAL
# =========================================================

class PayoutModal(
    discord.ui.Modal,
    title="Approve Submission"
):

    payout = discord.ui.TextInput(
        label="Payout",
        placeholder="$10 / $25 / 500 INR",
        required=True,
        max_length=50
    )

    def __init__(self, submission_id):

        super().__init__()

        self.submission_id = submission_id


    async def on_submit(
        self,
        interaction: discord.Interaction
    ):

        if not is_admin(interaction):

            await interaction.response.send_message(
                "❌ You don't have permission.",
                ephemeral=True
            )

            return

        payout = self.payout.value.strip()

        submission = database.get_submission(
            self.submission_id
        )

        if not submission:

            await interaction.response.send_message(
                "❌ Submission not found.",
                ephemeral=True
            )

            return

        if submission["status"] != "Pending":

            await interaction.response.send_message(
                "⚠️ This submission has already been reviewed.",
                ephemeral=True
            )

            return

        try:

            database.update_submission_status(
                submission_id=self.submission_id,
                status="Approved",
                payout=payout,
                reviewed_by=str(interaction.user)
            )

        except Exception as error:

            await interaction.response.send_message(
                f"❌ Database error:\n`{str(error)[:1000]}`",
                ephemeral=True
            )

            return

        # DM CLIPPER

        try:

            user = await bot.fetch_user(
                int(submission["discord_id"])
            )

            embed = discord.Embed(
                title="✅ Submission Approved!",
                description=(
                    f"Your submission **#{self.submission_id}** "
                    "has been approved."
                ),
                color=discord.Color.green()
            )

            embed.add_field(
                name="👀 Total Views",
                value=f"{submission['total_views']:,}",
                inline=True
            )

            embed.add_field(
                name="💰 Payout",
                value=payout,
                inline=True
            )

            await user.send(
                embed=embed
            )

        except Exception as error:

            print(
                f"⚠️ Could not DM clipper: {error}"
            )

        await interaction.response.send_message(
            f"✅ **Submission #{self.submission_id} Approved!**\n\n"
            f"💰 Payout: **{payout}**\n"
            f"📩 Clipper has been notified by DM.",
            ephemeral=True
        )


# =========================================================
# DECLINE MODAL
# =========================================================

class DeclineModal(
    discord.ui.Modal,
    title="Decline Submission"
):

    reason = discord.ui.TextInput(
        label="Decline Reason",
        placeholder="Enter reason...",
        required=True,
        style=discord.TextStyle.paragraph,
        max_length=500
    )

    def __init__(self, submission_id):

        super().__init__()

        self.submission_id = submission_id


    async def on_submit(
        self,
        interaction: discord.Interaction
    ):

        if not is_admin(interaction):

            await interaction.response.send_message(
                "❌ You don't have permission.",
                ephemeral=True
            )

            return

        submission = database.get_submission(
            self.submission_id
        )

        if not submission:

            await interaction.response.send_message(
                "❌ Submission not found.",
                ephemeral=True
            )

            return

        if submission["status"] != "Pending":

            await interaction.response.send_message(
                "⚠️ This submission has already been reviewed.",
                ephemeral=True
            )

            return

        reason = self.reason.value.strip()

        try:

            database.update_submission_status(
                submission_id=self.submission_id,
                status="Declined",
                payout=None,
                reviewed_by=str(interaction.user),
                decline_reason=reason
            )

        except Exception as error:

            await interaction.response.send_message(
                f"❌ Database error:\n`{str(error)[:1000]}`",
                ephemeral=True
            )

            return

        # DM CLIPPER

        try:

            user = await bot.fetch_user(
                int(submission["discord_id"])
            )

            embed = discord.Embed(
                title="❌ Submission Declined",
                description=(
                    f"Your submission **#{self.submission_id}** "
                    "has been declined."
                ),
                color=discord.Color.red()
            )

            embed.add_field(
                name="📌 Reason",
                value=reason,
                inline=False
            )

            await user.send(
                embed=embed
            )

        except Exception as error:

            print(
                f"⚠️ Could not DM clipper: {error}"
            )

        await interaction.response.send_message(
            f"❌ **Submission #{self.submission_id} Declined.**\n\n"
            f"Reason: **{reason}**\n"
            f"📩 Clipper has been notified by DM.",
            ephemeral=True
        )


# =========================================================
# SUBMISSION REVIEW VIEW
# =========================================================

class SubmissionReviewView(
    discord.ui.View
):

    def __init__(self, submission_id):

        super().__init__(
            timeout=900
        )

        self.submission_id = submission_id


    @discord.ui.button(
        label="Approve",
        emoji="✅",
        style=discord.ButtonStyle.success
    )
    async def approve(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        if not is_admin(interaction):

            await interaction.response.send_message(
                "❌ You don't have permission.",
                ephemeral=True
            )

            return

        submission = database.get_submission(
            self.submission_id
        )

        if not submission:

            await interaction.response.send_message(
                "❌ Submission not found.",
                ephemeral=True
            )

            return

        if submission["status"] != "Pending":

            await interaction.response.send_message(
                "⚠️ Already reviewed.",
                ephemeral=True
            )

            return

        await interaction.response.send_modal(
            PayoutModal(self.submission_id)
        )


    @discord.ui.button(
        label="Decline",
        emoji="❌",
        style=discord.ButtonStyle.danger
    )
    async def decline(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        if not is_admin(interaction):

            await interaction.response.send_message(
                "❌ You don't have permission.",
                ephemeral=True
            )

            return

        submission = database.get_submission(
            self.submission_id
        )

        if not submission:

            await interaction.response.send_message(
                "❌ Submission not found.",
                ephemeral=True
            )

            return

        if submission["status"] != "Pending":

            await interaction.response.send_message(
                "⚠️ Already reviewed.",
                ephemeral=True
            )

            return

        await interaction.response.send_modal(
            DeclineModal(self.submission_id)
        )


# =========================================================
# /SUBMISSION
# =========================================================

@bot.tree.command(
    name="submission",
    description="Review pending clipper submissions"
)
async def submission(
    interaction: discord.Interaction
):

    if not is_admin(interaction):

        await interaction.response.send_message(
            "❌ You don't have permission.",
            ephemeral=True
        )

        return

    try:

        pending = database.get_pending_submissions()

    except Exception as error:

        await interaction.response.send_message(
            f"❌ Database error:\n`{str(error)[:1000]}`",
            ephemeral=True
        )

        return

    if not pending:

        await interaction.response.send_message(
            "📭 **No pending submissions!**\n\n"
            "All submissions have been reviewed.",
            ephemeral=True
        )

        return

    await interaction.response.send_message(
        f"📥 **Pending Submissions: {len(pending)}**",
        ephemeral=True
    )

    for row in pending:

        submission_id = row[0]

        full_submission = database.get_submission(
            submission_id
        )

        if not full_submission:
            continue

        embed = create_submission_embed(
            full_submission
        )

        await interaction.followup.send(
            embed=embed,
            view=SubmissionReviewView(
                submission_id
            ),
            ephemeral=True
        )


# =========================================================
# /EXPORT_SUBMISSIONS
# =========================================================

@bot.tree.command(
    name="export_submissions",
    description="Export all submissions to Excel-compatible CSV"
)
async def export_submissions(
    interaction: discord.Interaction
):

    if not is_admin(interaction):

        await interaction.response.send_message(
            "❌ You don't have permission.",
            ephemeral=True
        )

        return

    try:

        submissions = database.get_all_submissions()

        if not submissions:

            await interaction.response.send_message(
                "📭 No submissions available to export.",
                ephemeral=True
            )

            return

        output = io.StringIO()

        writer = csv.writer(output)

        writer.writerow([
            "Submission ID",
            "Discord ID",
            "Discord Username",
            "Whop Username",
            "Google Drive Link",
            "Total Views",
            "Status",
            "Created At",
            "Week Start",
            "Payout",
            "Reviewed At",
            "Reviewed By",
            "Decline Reason",
            "Platform",
            "Account Username",
            "Account Views"
        ])

        for submission in submissions:

            (
                submission_id,
                discord_id,
                discord_username,
                whop_username,
                google_drive_link,
                total_views,
                status,
                created_at,
                week_start,
                payout,
                reviewed_at,
                reviewed_by,
                decline_reason
            ) = submission

            full_submission = database.get_submission(
                submission_id
            )

            accounts = full_submission["accounts"]

            if accounts:

                for account in accounts:

                    (
                        account_id,
                        platform,
                        username,
                        views
                    ) = account

                    writer.writerow([
                        submission_id,
                        discord_id,
                        discord_username,
                        whop_username,
                        google_drive_link,
                        total_views,
                        status,
                        created_at,
                        week_start,
                        payout or "",
                        reviewed_at or "",
                        reviewed_by or "",
                        decline_reason or "",
                        platform,
                        username,
                        views
                    ])

            else:

                writer.writerow([
                    submission_id,
                    discord_id,
                    discord_username,
                    whop_username,
                    google_drive_link,
                    total_views,
                    status,
                    created_at,
                    week_start,
                    payout or "",
                    reviewed_at or "",
                    reviewed_by or "",
                    decline_reason or "",
                    "",
                    "",
                    ""
                ])

        data = io.BytesIO(
            output.getvalue().encode("utf-8-sig")
        )

        file = discord.File(
            data,
            filename="CreativeXfame_submissions.csv"
        )

        await interaction.response.send_message(
            "📊 **All submissions exported successfully!**\n\n"
            "The CSV file can be opened directly in Excel.",
            file=file,
            ephemeral=True
        )

    except Exception as error:

        print("❌ EXPORT SUBMISSIONS ERROR:")
        print(error)

        await interaction.response.send_message(
            f"❌ Export failed:\n`{str(error)[:1500]}`",
            ephemeral=True
        )


# =========================================================
# CONFIGURATION
# =========================================================

if not TOKEN:

    raise RuntimeError(
        "❌ DISCORD_TOKEN is missing from .env"
    )


if GUILD_ID == 0:

    raise RuntimeError(
        "❌ GUILD_ID is missing from .env"
    )


# =========================================================
# START
# =========================================================

bot.run(TOKEN)