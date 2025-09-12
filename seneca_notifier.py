#!/usr/bin/env python3
import json
import requests
import time
import os
import hashlib
import argparse
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
from datetime import datetime


class SenecaNotifier:
    def __init__(self, config_file='config.json'):
        with open(config_file, 'r', encoding='utf-8') as f:
            self.config = json.load(f)
        
        self.data_file = self.config['data_file']
        self.processed_news = self.load_processed_news()
        
        # Configurar Chrome con más opciones para estabilidad
        self.chrome_options = Options()
        self.chrome_options.add_argument('--headless')
        self.chrome_options.add_argument('--no-sandbox')
        self.chrome_options.add_argument('--disable-dev-shm-usage')
        self.chrome_options.add_argument('--disable-gpu')
        self.chrome_options.add_argument('--disable-extensions')
        self.chrome_options.add_argument('--disable-plugins')
        self.chrome_options.add_argument('--disable-images')
        self.chrome_options.add_argument('--window-size=1920,1080')
        self.chrome_options.add_argument('--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        # Configurar el servicio de ChromeDriver
        self.service = None
    
    def load_processed_news(self):
        """Carga las noticias ya procesadas desde el archivo JSON"""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def save_processed_news(self):
        """Guarda las noticias procesadas en el archivo JSON"""
        with open(self.data_file, 'w', encoding='utf-8') as f:
            json.dump(self.processed_news, f, ensure_ascii=False, indent=2)
    
    def generate_news_hash(self, title, content=""):
        """Genera un hash único para una noticia"""
        return hashlib.md5((title + content).encode('utf-8')).hexdigest()
    
    def init_driver(self):
        """Inicializa el driver de Chrome con manejo de errores"""
        try:
            # Intentar con ChromeDriver local primero
            if os.path.exists('./chromedriver'):
                print("Usando ChromeDriver local...")
                self.service = Service('./chromedriver')
                driver = webdriver.Chrome(service=self.service, options=self.chrome_options)
                return driver
            
        except Exception as e:
            print(f"Error con ChromeDriver local: {e}")
        
        try:
            # Fallback: intentar usar ChromeDriverManager
            if self.service is None:
                print("Instalando/verificando ChromeDriver...")
                self.service = Service(ChromeDriverManager().install())
            
            driver = webdriver.Chrome(service=self.service, options=self.chrome_options)
            return driver
            
        except Exception as e:
            print(f"Error inicializando ChromeDriver con webdriver-manager: {e}")
            
            # Fallback final: intentar con driver del sistema
            try:
                print("Intentando con ChromeDriver del sistema...")
                driver = webdriver.Chrome(options=self.chrome_options)
                return driver
            except Exception as e2:
                print(f"Error con ChromeDriver del sistema: {e2}")
                raise Exception(f"No se pudo inicializar Chrome. Asegúrate de tener Chrome instalado: {e2}")
    
    def login_to_seneca(self, driver):
        """Realiza login en Séneca"""
        try:
            print(f"Navegando a: {self.config['seneca']['url']}")
            driver.get(self.config['seneca']['url'])
            
            # Esperar a que cargue la página
            time.sleep(3)
            print(f"Página cargada. Título: {driver.title}")
            
            # Buscar formulario de login con múltiples estrategias
            wait = WebDriverWait(driver, 15)
            
            username_field = None
            password_field = None
            
            # Estrategia 1: Por name (nombres correctos del portal)
            try:
                username_field = wait.until(EC.presence_of_element_located((By.NAME, 'USUARIO')))
                password_field = driver.find_element(By.NAME, 'CLAVE_P')
                print("Campos encontrados por 'name' (portal)")
            except:
                # Fallback a nombres antiguos
                try:
                    username_field = wait.until(EC.presence_of_element_located((By.NAME, 'usuario')))
                    password_field = driver.find_element(By.NAME, 'clave')
                    print("Campos encontrados por 'name' (pasen)")
                except:
                    print("No se encontraron campos por 'name'")
            
            # Estrategia 2: Por id
            if not username_field:
                try:
                    username_field = driver.find_element(By.ID, 'USUARIO')
                    password_field = driver.find_element(By.ID, 'CLAVE_P')
                    print("Campos encontrados por 'id' (portal)")
                except:
                    try:
                        username_field = driver.find_element(By.ID, 'usuario')
                        password_field = driver.find_element(By.ID, 'clave')
                        print("Campos encontrados por 'id' (pasen)")
                    except:
                        print("No se encontraron campos por 'id'")
            
            # Estrategia 3: Por tipo de input
            if not username_field:
                try:
                    inputs = driver.find_elements(By.XPATH, "//input[@type='text' or @type='email']")
                    password_inputs = driver.find_elements(By.XPATH, "//input[@type='password']")
                    
                    if inputs and password_inputs:
                        username_field = inputs[0]
                        password_field = password_inputs[0]
                        print("Campos encontrados por tipo de input")
                except:
                    print("No se encontraron campos por tipo")
            
            if not username_field or not password_field:
                print("No se pudieron encontrar los campos de login")
                print("HTML de la página:")
                print(driver.page_source[:1000])  # Primeros 1000 caracteres
                return False
            
            # Limpiar campos e introducir credenciales
            username_field.clear()
            password_field.clear()
            
            username_field.send_keys(self.config['seneca']['username'])
            password_field.send_keys(self.config['seneca']['password'])
            
            print("Credenciales introducidas")
            
            # Buscar botón de login con múltiples estrategias
            login_button = None
            
            # Estrategia 1: Botón type="button" con value="Entrar" (portal)
            try:
                login_button = driver.find_element(By.XPATH, "//input[@type='button'][@value='Entrar']")
                print("Botón encontrado: type=button value=Entrar")
            except:
                pass
            
            # Estrategia 2: Por value en cualquier tipo de botón
            if not login_button:
                try:
                    login_button = driver.find_element(By.XPATH, "//input[@value='Entrar' or contains(@value, 'Acceder') or contains(@value, 'Login')]")
                    print("Botón encontrado por value")
                except:
                    pass
            
            # Estrategia 3: Por texto del botón
            if not login_button:
                try:
                    login_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Entrar') or contains(text(), 'Acceder') or contains(text(), 'Login')]")
                    print("Botón encontrado por texto")
                except:
                    pass
            
            # Estrategia 4: Primer botón submit (fallback)
            if not login_button:
                try:
                    login_button = driver.find_element(By.XPATH, "//input[@type='submit']")
                    print("Botón encontrado: primer submit")
                except:
                    pass
            
            if login_button:
                print("Haciendo clic en botón de login")
                
                # Intentar clic normal primero
                try:
                    login_button.click()
                    print("Clic normal exitoso")
                except Exception as e:
                    print(f"Clic normal falló ({e}), intentando JavaScript...")
                    try:
                        driver.execute_script("arguments[0].click();", login_button)
                        print("Clic JavaScript exitoso")
                    except Exception as e2:
                        print(f"Clic JavaScript también falló: {e2}")
                        return False
                
                # Esperar a que se complete el login
                time.sleep(5)
                
                # Verificar si el login fue exitoso
                current_url = driver.current_url
                print(f"URL después del login: {current_url}")
                
                # Verificar diferentes indicadores de éxito
                # Si la URL cambió y contiene "nav/" significa que el login fue exitoso
                if (current_url != self.config['seneca']['url'] and 
                    ("nav/" in current_url or "pasen" in current_url.lower()) and
                    "error" not in current_url.lower()):
                    print("Login aparentemente exitoso")
                    return True
                else:
                    print("Login falló - verificar página actual")
                    print(f"URL original: {self.config['seneca']['url']}")
                    print(f"URL actual: {current_url}")
                    return False
                    
            else:
                print("No se encontró botón de login")
                return False
            
        except Exception as e:
            print(f"Error en login: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def click_messages_pending(self, driver):
        """Hace clic en 'Mensajes pendientes'"""
        try:
            wait = WebDriverWait(driver, 15)
            
            print("Buscando 'Mensajes pendientes' en la página...")
            
            # Primero, mostrar algunos enlaces para debug
            try:
                all_links = driver.find_elements(By.TAG_NAME, 'a')
                print(f"Encontrados {len(all_links)} enlaces en la página")
                
                # Mostrar primeros 10 enlaces para debug
                for i, link in enumerate(all_links[:10]):
                    try:
                        text = link.text.strip()
                        href = link.get_attribute('href')
                        if text:  # Solo mostrar enlaces con texto
                            print(f"  Enlace {i}: '{text}' -> {href}")
                    except:
                        continue
            except:
                pass
            
            # Buscar el enlace "Mensajes pendientes" por diferentes métodos
            messages_link = None
            
            # Intento 1: Por texto exacto
            try:
                messages_link = driver.find_element(By.LINK_TEXT, "Mensajes pendientes")
                print("✓ Encontrado por texto exacto: 'Mensajes pendientes'")
            except:
                pass
            
            # Intento 2: Por texto parcial
            if not messages_link:
                try:
                    messages_link = driver.find_element(By.PARTIAL_LINK_TEXT, "Mensajes")
                    print("✓ Encontrado por texto parcial: 'Mensajes'")
                except:
                    pass
            
            # Intento 3: Por xpath más genérico (insensible a mayúsculas)
            if not messages_link:
                try:
                    messages_link = driver.find_element(By.XPATH, "//a[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'mensajes')]")
                    print("✓ Encontrado por xpath insensible a mayúsculas")
                except:
                    pass
            
            # Intento 4: Buscar cualquier elemento que contenga "mensajes"
            if not messages_link:
                try:
                    elements = driver.find_elements(By.XPATH, "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'mensajes')]")
                    if elements:
                        messages_link = elements[0]
                        print(f"✓ Encontrado elemento genérico con 'mensajes': {messages_link.tag_name}")
                except:
                    pass
            
            # Intento 5: Buscar por "PASEN" o "Pasen"
            if not messages_link:
                try:
                    messages_link = driver.find_element(By.PARTIAL_LINK_TEXT, "PASEN")
                    print("✓ Encontrado enlace con 'PASEN'")
                except:
                    try:
                        messages_link = driver.find_element(By.PARTIAL_LINK_TEXT, "Pasen")
                        print("✓ Encontrado enlace con 'Pasen'")
                    except:
                        pass
            
            if messages_link:
                print(f"Haciendo clic en: '{messages_link.text}'")
                try:
                    messages_link.click()
                    print("✓ Clic exitoso")
                except Exception as e:
                    print(f"Clic normal falló, intentando JavaScript: {e}")
                    driver.execute_script("arguments[0].click();", messages_link)
                    print("✓ Clic JavaScript exitoso")
                
                time.sleep(3)
                print(f"Nueva URL después del clic: {driver.current_url}")
                return True
            else:
                print("✗ No se pudo encontrar el enlace 'Mensajes pendientes'")
                print("\nTodos los enlaces disponibles:")
                try:
                    all_links = driver.find_elements(By.TAG_NAME, 'a')
                    for i, link in enumerate(all_links):
                        try:
                            text = link.text.strip()
                            if text:
                                print(f"  {i}: '{text}'")
                        except:
                            continue
                except:
                    pass
                return False
                
        except Exception as e:
            print(f"Error al hacer clic en mensajes pendientes: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def extract_news(self, driver):
        """Extrae las noticias de la página"""
        news_list = []
        
        try:
            # Esperar a que cargue la página de mensajes
            wait = WebDriverWait(driver, 10)
            time.sleep(2)  # Tiempo adicional para asegurar carga completa
            
            print("Buscando tabla de noticias...")
            
            # Buscar todas las tablas
            tables = driver.find_elements(By.TAG_NAME, 'table')
            print(f"Encontradas {len(tables)} tablas")
            
            if len(tables) > 1:
                # Usar la Tabla 1 (índice 1) que contiene las noticias
                news_table = tables[1]
                print("Usando Tabla 1 para extraer noticias")
                
                # Buscar todas las filas de la tabla
                rows = news_table.find_elements(By.TAG_NAME, 'tr')
                print(f"Encontradas {len(rows)} filas en la tabla de noticias")
                
                # Saltar la primera fila si es header
                start_row = 1 if len(rows) > 1 else 0
                
                for i, row in enumerate(rows[start_row:], start_row):
                    try:
                        cells = row.find_elements(By.TAG_NAME, 'td')
                        if not cells:
                            continue
                        
                        # Extraer información de las celdas específicas según la estructura conocida
                        title = ""
                        content = ""
                        date_info = ""
                        sender = ""
                        read_date = ""
                        
                        # Verificar que tenemos suficientes celdas
                        if len(cells) >= 8:
                            # Celda 1: Fecha de entrada
                            date_info = cells[1].text.strip() if len(cells) > 1 else ""
                            
                            # Celda 5: Asunto (TÍTULO de la noticia)
                            title = cells[5].text.strip() if len(cells) > 5 else ""
                            
                            # Celda 6: Remitido por
                            sender = cells[6].text.strip() if len(cells) > 6 else ""
                            
                            # Celda 7: Fecha de lectura
                            read_date = cells[7].text.strip() if len(cells) > 7 else ""
                        
                        # Si no encontramos título en celda 5, buscar en otras celdas
                        if not title:
                            for cell in cells:
                                cell_text = cell.text.strip()
                                if cell_text and len(cell_text) > 5 and not cell_text.startswith('0') and '/' not in cell_text:
                                    title = cell_text
                                    break
                        
                        # Construir contenido informativo
                        content_parts = []
                        if date_info:
                            content_parts.append(f"📅 Fecha: {date_info}")
                        if sender:
                            content_parts.append(f"👤 Remitido por: {sender}")
                        if read_date:
                            content_parts.append(f"👀 Leído: {read_date}")
                        else:
                            content_parts.append("📢 Mensaje nuevo")
                        
                        content = "\n".join(content_parts)
                        
                        # Verificar que tenemos contenido válido
                        if title and len(title) > 3:
                            news_hash = self.generate_news_hash(title, content)
                            
                            news_item = {
                                'hash': news_hash,
                                'title': title,
                                'content': content,
                                'timestamp': datetime.now().isoformat()
                            }
                            
                            news_list.append(news_item)
                            print(f"Noticia extraída: '{title[:50]}...'")
                            
                    except Exception as e:
                        print(f"Error procesando fila {i}: {e}")
                        continue
            
            else:
                print("No se encontró la tabla de noticias esperada")
                # Fallback a método anterior
                news_elements = driver.find_elements(By.XPATH, "//tr[td]")
                
                for element in news_elements:
                    try:
                        text = element.text.strip()
                        if text and len(text) > 10:
                            # Usar primeras palabras como título
                            words = text.split()
                            title = " ".join(words[:6]) if len(words) >= 6 else text
                            
                            news_hash = self.generate_news_hash(title, text)
                            
                            news_item = {
                                'hash': news_hash,
                                'title': title,
                                'content': text,
                                'timestamp': datetime.now().isoformat()
                            }
                            
                            news_list.append(news_item)
                            
                    except Exception as e:
                        continue
            
            print(f"Total de noticias extraídas: {len(news_list)}")
            
        except Exception as e:
            print(f"Error extrayendo noticias: {e}")
            import traceback
            traceback.print_exc()
        
        return news_list
    
    def send_telegram_message(self, message):
        """Envía un mensaje por Telegram"""
        try:
            url = f"https://api.telegram.org/bot{self.config['telegram']['bot_token']}/sendMessage"
            
            data = {
                'chat_id': self.config['telegram']['chat_id'],
                'text': message,
                'parse_mode': 'HTML'
            }
            
            response = requests.post(url, data=data)
            return response.status_code == 200
            
        except Exception as e:
            print(f"Error enviando mensaje por Telegram: {e}")
            return False
    
    def process_new_news(self, news_list):
        """Procesa las noticias nuevas y envía por Telegram"""
        new_news_count = 0
        
        for news in news_list:
            if news['hash'] not in self.processed_news:
                # Nueva noticia encontrada
                self.processed_news[news['hash']] = {
                    'title': news['title'],
                    'processed_at': datetime.now().isoformat()
                }
                
                # Formatear mensaje para Telegram
                message = f"📢 <b>Nueva noticia en Séneca</b>\n\n"
                message += f"<b>{news['title']}</b>\n\n"
                message += f"{news['content'][:500]}"
                if len(news['content']) > 500:
                    message += "..."
                
                message += f"\n\n🕐 {datetime.now().strftime('%d/%m/%Y %H:%M')}"
                
                # Enviar por Telegram
                if self.send_telegram_message(message):
                    print(f"Noticia enviada: {news['title'][:50]}...")
                    new_news_count += 1
                else:
                    print(f"Error enviando noticia: {news['title'][:50]}...")
        
        # Guardar las noticias procesadas
        if new_news_count > 0:
            self.save_processed_news()
        
        return new_news_count
    
    def run(self):
        """Ejecuta el proceso completo"""
        driver = None
        
        try:
            print(f"[{datetime.now()}] Iniciando proceso...")
            
            # Inicializar driver
            driver = self.init_driver()
            
            # Login en Séneca
            if not self.login_to_seneca(driver):
                print("Error en el login")
                return
            
            print("Login exitoso")
            
            # Hacer clic en "Mensajes pendientes"
            if not self.click_messages_pending(driver):
                print("Error accediendo a mensajes pendientes")
                return
            
            print("Accedido a mensajes pendientes")
            
            # Extraer noticias
            news_list = self.extract_news(driver)
            print(f"Extraídas {len(news_list)} noticias")
            
            # Procesar noticias nuevas
            new_count = self.process_new_news(news_list)
            
            if new_count > 0:
                print(f"Se enviaron {new_count} noticias nuevas")
            else:
                print("No hay noticias nuevas")
                
        except Exception as e:
            print(f"Error general: {e}")
            
        finally:
            if driver:
                driver.quit()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Monitor Séneca for new messages')
    parser.add_argument('-c', '--config', default='config.json', 
                       help='Configuration file path (default: config.json)')
    
    args = parser.parse_args()
    
    notifier = SenecaNotifier(args.config)
    notifier.run()