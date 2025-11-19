import re
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from card_parser import parse_card_input
from api_client import api_client
from response_formatter import format_api_response, format_bin_response, format_gen_response, format_crunchyroll_response, format_error_message, start_timer
from security import can_use_command, is_allowed_chat, is_owner, get_cooldown_status, get_chat_permissions, add_allowed_chat, remove_allowed_chat, get_allowed_chats
from payment_processor import process_card_payment
from tempest_client import authnet_command
from stripe9_client import run_stripe9_check
from shopify1_client import s1_command  # NUOVO IMPORT

logger = logging.getLogger(__name__)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Main bot menu"""
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    chat_type = update.effective_chat.type
    
    if not is_allowed_chat(chat_id, chat_type, user_id):
        permission_info = get_chat_permissions(chat_id, chat_type, user_id)
        await update.message.reply_text(f"❌ {permission_info}")
        return
    
    keyboard = [
        [InlineKeyboardButton("Gates", callback_data="gates")],
        [InlineKeyboardButton("Utility", callback_data="utility")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    cooldown_status = get_cooldown_status(user_id)
    permission_info = get_chat_permissions(chat_id, chat_type, user_id)
    
    message_text = f"What would you like to do today?\n\n{permission_info}\n{cooldown_status}"
    await update.message.reply_text(message_text, reply_markup=reply_markup)

async def cmds_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start_command(update, context)

async def cmd_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start_command(update, context)

async def id_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    chat_type = update.effective_chat.type
    
    user_first_name = update.effective_user.first_name
    user_username = update.effective_user.username
    
    if chat_type == "private":
        chat_info = "Private Chat"
    elif chat_type == "group":
        chat_info = "Group"
    elif chat_type == "supergroup":
        chat_info = "Supergroup"
    elif chat_type == "channel":
        chat_info = "Channel"
    else:
        chat_info = "Unknown"
    
    response = f"""🆔 **ID Information**

👤 **Your User ID:** `{user_id}`
👥 **Chat ID:** `{chat_id}`
💬 **Chat Type:** {chat_type} ({chat_info})

👨 **User:** {user_first_name}
📱 **Username:** @{user_username if user_username else 'N/A'}

🔒 **Permission Status:** {get_chat_permissions(chat_id, chat_type, user_id)}"""

    await update.message.reply_text(response)

async def allow_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not is_owner(user_id):
        await update.message.reply_text("❌ This command is only available for the bot owner.")
        return
    
    chat_id = update.effective_chat.id
    chat_type = update.effective_chat.type
    
    if context.args:
        try:
            target_chat_id = int(context.args[0])
            chat_id = target_chat_id
            chat_type = "unknown"
        except ValueError:
            await update.message.reply_text("❌ Invalid chat ID. Please provide a valid numeric ID.")
            return
    
    if add_allowed_chat(chat_id):
        response = f"""✅ **Chat Added to Allowed List**

👥 **Chat ID:** `{chat_id}`
💬 **Chat Type:** {chat_type}

🔓 **Status:** This chat can now use the bot commands"""
    else:
        response = f"""ℹ️ **Chat Already Allowed**

👥 **Chat ID:** `{chat_id}`
💬 **Chat Type:** {chat_type}

🔓 **Status:** This chat is already in the allowed list"""
    
    await update.message.reply_text(response)

async def disallow_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not is_owner(user_id):
        await update.message.reply_text("❌ This command is only available for the bot owner.")
        return
    
    chat_id = update.effective_chat.id
    
    if context.args:
        try:
            target_chat_id = int(context.args[0])
            chat_id = target_chat_id
        except ValueError:
            await update.message.reply_text("❌ Invalid chat ID. Please provide a valid numeric ID.")
            return
    
    if remove_allowed_chat(chat_id):
        response = f"""❌ **Chat Removed from Allowed List**

👥 **Chat ID:** `{chat_id}`

🔒 **Status:** This chat can no longer use the bot commands"""
    else:
        response = f"""ℹ️ **Chat Not in Allowed List**

👥 **Chat ID:** `{chat_id}`

🔒 **Status:** This chat was not in the allowed list"""
    
    await update.message.reply_text(response)

async def list_allowed_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not is_owner(user_id):
        await update.message.reply_text("❌ This command is only available for the bot owner.")
        return
    
    allowed_chats = get_allowed_chats()
    
    if not allowed_chats:
        response = "📋 **Allowed Chats List**\n\nNo chats are currently allowed."
    else:
        response = "📋 **Allowed Chats List**\n\n"
        for i, chat_id in enumerate(allowed_chats, 1):
            response += f"{i}. `{chat_id}`\n"
        
        response += f"\n**Total:** {len(allowed_chats)} chat(s)"
    
    await update.message.reply_text(response)

async def gates_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    chat_type = update.effective_chat.type
    
    if not is_allowed_chat(chat_id, chat_type, user_id):
        return
    
    cooldown_status = get_cooldown_status(user_id)
    permission_info = get_chat_permissions(chat_id, chat_type, user_id)
    
    keyboard = [
        [InlineKeyboardButton("Stripe $1", callback_data="gate_stripe1")],
        [InlineKeyboardButton("Stripe $5", callback_data="gate_stripe5")],
        [InlineKeyboardButton("Stripe $9", callback_data="gate_stripe9")],
        [InlineKeyboardButton("Shopify $1", callback_data="gate_shopify")],
        [InlineKeyboardButton("AuthNet $300", callback_data="gate_authnet")],
        [InlineKeyboardButton("Caliper", callback_data="gate_caliper")],
        [InlineKeyboardButton("🔙 Back", callback_data="back_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"Available Gates\n\n{permission_info}\n{cooldown_status}",
        reply_markup=reply_markup
    )

async def utility_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    chat_type = update.effective_chat.type
    
    if not is_allowed_chat(chat_id, chat_type, user_id):
        return
    
    permission_info = get_chat_permissions(chat_id, chat_type, user_id)
    
    keyboard = [
        [InlineKeyboardButton("BIN Lookup", callback_data="util_bin")],
        [InlineKeyboardButton("Generate Cards", callback_data="util_gen")],
        [InlineKeyboardButton("Crunchyroll", callback_data="util_crunchy")],
        [InlineKeyboardButton("🔙 Back", callback_data="back_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"Utility Tools\n\n{permission_info}",
        reply_markup=reply_markup
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    chat_id = query.message.chat.id
    chat_type = query.message.chat.type
    
    if not is_allowed_chat(chat_id, chat_type, user_id):
        permission_info = get_chat_permissions(chat_id, chat_type, user_id)
        await query.edit_message_text(f"❌ {permission_info}")
        return
    
    data = query.data
    
    if data == "gates":
        cooldown_status = get_cooldown_status(user_id)
        permission_info = get_chat_permissions(chat_id, chat_type, user_id)
        keyboard = [
            [InlineKeyboardButton("Stripe $1", callback_data="gate_stripe1")],
            [InlineKeyboardButton("Stripe $5", callback_data="gate_stripe5")],
            [InlineKeyboardButton("Stripe $9", callback_data="gate_stripe9")],
            [InlineKeyboardButton("Shopify $1", callback_data="gate_shopify")],
            [InlineKeyboardButton("authnet $32", callback_data="gate_authnet")],
            [InlineKeyboardButton("braintree auth (wip)", callback_data="gate_caliper")],
            [InlineKeyboardButton("🔙 Back", callback_data="back_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(f"Available Gates\n\n{permission_info}\n{cooldown_status}", reply_markup=reply_markup)
    
    elif data == "utility":
        permission_info = get_chat_permissions(chat_id, chat_type, user_id)
        keyboard = [
            [InlineKeyboardButton("BIN Lookup", callback_data="util_bin")],
            [InlineKeyboardButton("Generate Cards", callback_data="util_gen")],
            [InlineKeyboardButton("Crunchyroll", callback_data="util_crunchy")],
            [InlineKeyboardButton("🔙 Back", callback_data="back_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(f"Utility Tools\n\n{permission_info}", reply_markup=reply_markup)
    
    elif data == "back_main":
        cooldown_status = get_cooldown_status(user_id)
        permission_info = get_chat_permissions(chat_id, chat_type, user_id)
        keyboard = [
            [InlineKeyboardButton("Gates", callback_data="gates")],
            [InlineKeyboardButton("Utility", callback_data="utility")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(f"What would you like to do today?\n\n{permission_info}\n{cooldown_status}", reply_markup=reply_markup)
    
    elif data.startswith("gate_"):
        gate_type = data.split("_")[1]
        cooldown_status = get_cooldown_status(user_id)
        permission_info = get_chat_permissions(chat_id, chat_type, user_id)
        if gate_type == "authnet":
            await query.edit_message_text(f"Usage: /au number|month|year|cvv [proxy]\n\nExample: 4147400214647297|12|2026|123\nExample with proxy: 4147400214647297|12|2026|123 http://proxy-ip:port\n\n{permission_info}\n{cooldown_status}")
        elif gate_type == "caliper":
            await query.edit_message_text(f"Usage: /caliper number|month|year|cvv [proxy]\n\nExample: 4147768578745265|04|2026|168\nExample with proxy: 4147768578745265|04|2026|168 http://proxy-ip:port\n\n{permission_info}\n{cooldown_status}")
        elif gate_type == "stripe9":
            await query.edit_message_text(f"Usage: /st9 number|month|year|cvv [proxy]\n\nExample: 4111111111111111|12|2028|123\nExample with proxy: 4111111111111111|12|2028|123 http://proxy-ip:port\n\n{permission_info}\n{cooldown_status}")
        elif gate_type == "shopify":
            await query.edit_message_text(f"Usage: /s1 number|month|year|cvv [proxy]\n\nExample: 4111111111111111|12|2028|123\nExample with proxy: 4111111111111111|12|2028|123 http://proxy-ip:port\n\n{permission_info}\n{cooldown_status}")
        else:
            await query.edit_message_text(f"Usage: /{gate_type} number|month|year|cvv\n\nExample: 4147768578745265|04|2026|168\n\n{permission_info}\n{cooldown_status}")
    
    elif data.startswith("util_"):
        util_type = data.split("_")[1]
        if util_type == "bin":
            await query.edit_message_text("Usage: /bin xxxxxx\n\nExample: /bin 457381")
        elif util_type == "gen":
            await query.edit_message_text("Usage: /gen xxxxxx\n\nExample: /gen 559888")
        elif util_type == "crunchy":
            await query.edit_message_text("Usage: /crunchy email:password\n\nExample: /crunchy user@example.com:password123")

async def check_card_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _check_card_gateway(update, context, 'chk')

async def stripe5_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _check_card_gateway(update, context, 'st5')

async def stripe9_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check card with Stripe $9 Gateway"""
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    chat_type = update.effective_chat.type
    
    if not is_allowed_chat(chat_id, chat_type, user_id):
        permission_info = get_chat_permissions(chat_id, chat_type, user_id)
        await update.message.reply_text(f"❌ {permission_info}")
        return
    
    can_use, error_msg = can_use_command(user_id, 'st9')
    if not can_use:
        await update.message.reply_text(error_msg)
        return
    
    if not context.args:
        await update.message.reply_text(
            "🎯 **Stripe $9 Gateway Check**\n\n"
            "Usage: /st9 number|month|year|cvv [proxy]\n\n"
            "Example: /st9 4111111111111111|12|2028|123\n"
            "With proxy: /st9 4111111111111111|12|2028|123 http://proxy-ip:port"
        )
        return
    
    # COMBINE ALL ARGUMENTS
    full_input = ' '.join(context.args)
    logger.info(f"🔍 Full input: {full_input}")
    
    # FIND PROXY
    proxy_match = re.search(r'(https?://[^\s]+)', full_input)
    proxy_url = proxy_match.group(0) if proxy_match else None
    
    # REMOVE PROXY FROM INPUT
    if proxy_url:
        card_input = full_input.replace(proxy_url, '').strip()
        logger.info(f"🔌 Proxy found: {proxy_url}")
    else:
        card_input = full_input
    
    # CLEAN SPACES
    card_input = re.sub(r'\s+', ' ', card_input).strip()
    
    if proxy_url:
        wait_message = await update.message.reply_text(f"🔄 Checking Stripe $9 with proxy...")
    else:
        wait_message = await update.message.reply_text("🔄 Checking Stripe $9...")
    
    try:
        parsed_card = parse_card_input(card_input)
        
        if not parsed_card['valid']:
            await wait_message.edit_text(format_error_message('invalid_format', parsed_card['error']))
            return
        
        logger.info(f"🎯 Card parsed: {parsed_card['number'][:6]}******{parsed_card['number'][-4:]}")
        
        # GET BIN INFORMATION
        bin_number = parsed_card['number'][:6]
        bin_result = api_client.bin_lookup(bin_number)
        
        # EXECUTE STRIPE $9 CHECK
        status, message = run_stripe9_check(
            parsed_card['number'],
            parsed_card['month'],
            parsed_card['year'],
            parsed_card['cvv'],
            proxy_url=proxy_url
        )
        
        # FORMAT RESPONSE
        if status == "APPROVED":
            response = f"""Approved ✅

Card: {parsed_card['number']}|{parsed_card['month']}|{parsed_card['year']}|{parsed_card['cvv']}
Gateway: Stripe $9
Response: {message}"""
        elif status == "DECLINED":
            response = f"""Declined ❌

Card: {parsed_card['number']}|{parsed_card['month']}|{parsed_card['year']}|{parsed_card['cvv']}
Gateway: Stripe $9
Response: {message}"""
        elif status == "PROCESSING":
            response = f"""Processing 🔄

Card: {parsed_card['number']}|{parsed_card['month']}|{parsed_card['year']}|{parsed_card['cvv']}
Gateway: Stripe $9
Response: {message}"""
        else:
            response = f"""Error ⚠️

Card: {parsed_card['number']}|{parsed_card['month']}|{parsed_card['year']}|{parsed_card['cvv']}
Gateway: Stripe $9
Response: {message}"""
        
        # ADD BIN INFO IF AVAILABLE
        if bin_result and bin_result['success']:
            bin_data = bin_result['data']
            response += f"""

BIN Info:
Country: {bin_data.get('country', 'N/A')}
Issuer: {bin_data.get('issuer', 'N/A')}
Scheme: {bin_data.get('scheme', 'N/A')}
Type: {bin_data.get('type', 'N/A')}
Tier: {bin_data.get('tier', 'N/A')}"""
        
        await wait_message.edit_text(response)
        
    except Exception as e:
        logger.error(f"❌ Error in stripe9_command: {e}")
        await wait_message.edit_text(f"❌ Error: {str(e)}")

# RIMUOVI IL VECCHIO SHOPIFY_COMMAND CHE USA L'API
# async def shopify_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     await _check_card_gateway(update, context, 'sh')

async def authnet_command_wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Wrapper for /au command - now uses AuthNet Gate"""
    await authnet_command(update, context)

async def caliper_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check card on CaliperCovers with proxy support"""
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    chat_type = update.effective_chat.type
    
    if not is_allowed_chat(chat_id, chat_type, user_id):
        permission_info = get_chat_permissions(chat_id, chat_type, user_id)
        await update.message.reply_text(f"❌ {permission_info}")
        return
    
    can_use, error_msg = can_use_command(user_id, 'caliper')
    if not can_use:
        await update.message.reply_text(error_msg)
        return
    
    if not context.args:
        await update.message.reply_text("❌ Usage: /caliper number|month|year|cvv [proxy]\n\nExample: 4111111111111111|12|2028|123\nWith proxy: 4111111111111111|12|2028|123 http://proxy-ip:port")
        return
    
    # COMBINE ALL ARGUMENTS INTO ONE STRING
    full_input = ' '.join(context.args)
    logger.info(f"🔍 Full input: {full_input}")
    
    # FIND PROXY (http:// or https://)
    proxy_match = re.search(r'(https?://[^\s]+)', full_input)
    proxy_url = proxy_match.group(0) if proxy_match else None
    
    # REMOVE PROXY FROM CARD INPUT
    if proxy_url:
        card_input = full_input.replace(proxy_url, '').strip()
        logger.info(f"🔌 Proxy found: {proxy_url}")
        logger.info(f"💳 Clean card input: {card_input}")
    else:
        card_input = full_input
        logger.info(f"💳 Card input (no proxy): {card_input}")
    
    # CLEAN EXTRA SPACES
    card_input = re.sub(r'\s+', ' ', card_input).strip()
    
    if proxy_url:
        wait_message = await update.message.reply_text(f"🔄 Checking CaliperCovers with proxy...")
    else:
        wait_message = await update.message.reply_text("🔄 Checking CaliperCovers...")
    
    try:
        parsed_card = parse_card_input(card_input)
        
        if not parsed_card['valid']:
            await wait_message.edit_text(format_error_message('invalid_format', parsed_card['error']))
            return
        
        logger.info(f"🎯 Card parsed: {parsed_card['number'][:6]}******{parsed_card['number'][-4:]}")
        
        # EXECUTE CALIPER CHECK WITH PROXY
        result = process_card_payment(
            parsed_card['number'],
            parsed_card['month'] + parsed_card['year'][-2:],
            parsed_card['cvv'],
            proxy_url=proxy_url
        )
        
        # FORMAT RESULT
        response = f"""🎯 **CaliperCovers Check** {'🔌' if proxy_url else ''}

💳 **Card:** `{parsed_card['number'][:6]}******{parsed_card['number'][-4:]}`
📅 **Date:** `{parsed_card['month']}/{parsed_card['year']}`
🔒 **CVV:** `{parsed_card['cvv']}`
{'🔌 **Proxy:** ' + proxy_url if proxy_url else ''}

📊 **Result:** {result}"""
        
        await wait_message.edit_text(response)
        
    except Exception as e:
        logger.error(f"❌ Error in caliper_command: {e}")
        await wait_message.edit_text(f"❌ Error: {str(e)}")

async def _check_card_gateway(update: Update, context: ContextTypes.DEFAULT_TYPE, command: str):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    chat_type = update.effective_chat.type
    
    if not is_allowed_chat(chat_id, chat_type, user_id):
        permission_info = get_chat_permissions(chat_id, chat_type, user_id)
        await update.message.reply_text(f"❌ {permission_info}")
        return
    
    can_use, error_msg = can_use_command(user_id, command)
    if not can_use:
        await update.message.reply_text(error_msg)
        return
    
    if not context.args:
        await update.message.reply_text(f"❌ Usage: /{command} number|month|year|cvv")
        return
    
    card_input = ' '.join(context.args)
    wait_message = await update.message.reply_text(f"🔄 Checking card...")
    start_timer()
    
    try:
        parsed_card = parse_card_input(card_input)
        
        if not parsed_card['valid']:
            await wait_message.edit_text(format_error_message('invalid_format', parsed_card['error']))
            return
        
        bin_number = parsed_card['number'][:6]
        bin_result = api_client.bin_lookup(bin_number)
        
        gateways = {
            'chk': 'stripe1',
            'st5': 'stripe5', 
            'sh': 'shopify'
        }
        
        api_result = api_client.check_card(parsed_card['card_data'], gateway=gateways[command])
        response_text = format_api_response(parsed_card, api_result, bin_result)
        await wait_message.edit_text(response_text)
        
    except Exception as e:
        await wait_message.edit_text(format_error_message('api_error', str(e)))

async def crunchyroll_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    chat_type = update.effective_chat.type
    
    if not is_allowed_chat(chat_id, chat_type, user_id):
        permission_info = get_chat_permissions(chat_id, chat_type, user_id)
        await update.message.reply_text(f"❌ {permission_info}")
        return
    
    if not context.args:
        await update.message.reply_text("❌ Usage: /crunchy email:password")
        return
    
    credentials = ' '.join(context.args)
    wait_message = await update.message.reply_text("🔄 Checking account...")
    start_timer()
    
    try:
        if ':' not in credentials:
            await wait_message.edit_text(format_error_message('invalid_credentials', "Format must be email:password"))
            return
        
        api_result = api_client.check_crunchyroll(credentials)
        response_text = format_crunchyroll_response(api_result)
        await wait_message.edit_text(response_text)
        
    except Exception as e:
        await wait_message.edit_text(format_error_message('api_error', str(e)))

async def bin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    chat_type = update.effective_chat.type
    
    if not is_allowed_chat(chat_id, chat_type, user_id):
        permission_info = get_chat_permissions(chat_id, chat_type, user_id)
        await update.message.reply_text(f"❌ {permission_info}")
        return
    
    if not context.args:
        await update.message.reply_text("❌ Usage: /bin xxxxxx")
        return
    
    bin_number = context.args[0].strip()
    wait_message = await update.message.reply_text("🔄 Looking up BIN...")
    start_timer()
    
    try:
        if len(bin_number) < 6 or not bin_number.isdigit():
            await wait_message.edit_text(format_error_message('invalid_bin', "BIN must be at least 6 digits"))
            return
        
        bin_result = api_client.bin_lookup(bin_number)
        response_text = format_bin_response(bin_result)
        await wait_message.edit_text(response_text)
        
    except Exception as e:
        await wait_message.edit_text(format_error_message('api_error', str(e)))

async def gen_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    chat_type = update.effective_chat.type
    
    if not is_allowed_chat(chat_id, chat_type, user_id):
        permission_info = get_chat_permissions(chat_id, chat_type, user_id)
        await update.message.reply_text(f"❌ {permission_info}")
        return
    
    if not context.args:
        await update.message.reply_text("❌ Usage: /gen xxxxxx")
        return
    
    bin_number = context.args[0].strip()
    wait_message = await update.message.reply_text("🔄 Generating cards...")
    start_timer()
    
    try:
        if len(bin_number) < 6 or not bin_number.isdigit():
            await wait_message.edit_text(format_error_message('invalid_bin', "BIN must be at least 6 digits"))
            return
        
        gen_result = api_client.generate_cards(bin_number)
        response_text = format_gen_response(gen_result)
        await wait_message.edit_text(response_text)
        
    except Exception as e:
        await wait_message.edit_text(format_error_message('api_error', str(e)))

async def handle_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    chat_type = update.effective_chat.type
    
    if is_allowed_chat(chat_id, chat_type, user_id) and not update.message.text.startswith('/'):
        await start_command(update, context)

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Error: {context.error}")
