import os
import time
import json
import base64
import random
import hashlib
import tkinter as tk
from tkinter import ttk, scrolledtext
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from webdriver_manager.chrome import ChromeDriverManager
from PIL import Image, ImageTk
import cv2
import numpy as np
import openai
from dotenv import load_dotenv

load_dotenv()

class SparxMathsSolver:
    def __init__(self, root):
        self.root = root
        self.root.title("Sparx Maths Solver Pro")
        self.root.geometry("1400x950")
        
        # State management
        self.is_running = False
        self.answers_db = {}
        self.driver = None
        self.current_question_image = None
        self.current_bookwork_code = None

        # Initialize UI components
        self.setup_ui()
        self.load_answers()
        self.setup_shortcuts()

    def setup_ui(self):
        """Configure all user interface elements"""
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Control Panel
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill=tk.X, pady=5)

        ttk.Label(control_frame, text="Username:").grid(row=0, column=0, padx=5)
        self.username_entry = ttk.Entry(control_frame, width=25)
        self.username_entry.grid(row=0, column=1, padx=5)

        ttk.Label(control_frame, text="Password:").grid(row=0, column=2, padx=5)
        self.password_entry = ttk.Entry(control_frame, show="*", width=25)
        self.password_entry.grid(row=0, column=3, padx=5)

        ttk.Label(control_frame, text="OpenAI Key:").grid(row=0, column=4, padx=5)
        self.openai_entry = ttk.Entry(control_frame, width=35)
        self.openai_entry.grid(row=0, column=5, padx=5)

        self.start_btn = ttk.Button(control_frame, text="Start", command=self.start_solver)
        self.start_btn.grid(row=0, column=6, padx=5)
        self.stop_btn = ttk.Button(control_frame, text="Stop", command=self.stop_solver, state=tk.DISABLED)
        self.stop_btn.grid(row=0, column=7, padx=5)

        # Question Display Area
        self.canvas_frame = ttk.Frame(main_frame)
        self.canvas_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        self.question_canvas = tk.Canvas(self.canvas_frame, width=1100, height=550, bg='white')
        self.question_canvas.pack(fill=tk.BOTH, expand=True)

        # Log System
        self.log_text = scrolledtext.ScrolledText(main_frame, height=18, wrap=tk.WORD)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(main_frame, textvariable=self.status_var, foreground="blue").pack(anchor=tk.W)

    def setup_shortcuts(self):
        """Configure keyboard shortcuts"""
        self.root.bind('<Control-q>', lambda e: self.stop_solver())
        self.root.bind('<F5>', lambda e: self.refresh_ui())

    def refresh_ui(self):
        """Refresh UI components"""
        self.question_canvas.delete("all")
        self.log_text.delete(1.0, tk.END)
        self.status_var.set("UI Refreshed")
        self.root.update()

    # Core solver functionality
    def start_solver(self):
        """Main entry point for solving process"""
        if self.is_running: return
        self.is_running = True
        self.toggle_controls()
        
        try:
            self.initialize_browser()
            self.login_to_sparx(
                self.username_entry.get() or os.getenv("SPARX_USERNAME"),
                self.password_entry.get() or os.getenv("SPARX_PASSWORD")
            )
            if not self.navigate_to_first_incomplete_task():
                raise Exception("No incomplete tasks found")
            self.solving_loop()
        except Exception as e:
            self.log(f"Fatal initialization error: {str(e)}", error=True)
            self.stop_solver()

    def navigate_to_first_incomplete_task(self):
        """Selects and clicks the first incomplete task"""
        try:
            self.log("Locating incomplete tasks...")
            
            # Wait for tasks to load
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "a[href*='/task/']"))
            )

            # Find all task links with "Start" indication (incomplete tasks)
            task_links = self.driver.find_elements(
                By.XPATH,
                "//a[contains(@class, '_TaskClickable_') and .//div[contains(@class, '_TaskChip_') and contains(text(), 'Start')]]"
            )

            if not task_links:
                self.log("No incomplete tasks found")
                return False
            
            # Get the first incomplete task
            incomplete_task = task_links[0]
            
            # Scroll to and click the task
            self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", incomplete_task)
            time.sleep(1)
            
            # Click using JavaScript to avoid interception issues
            self.driver.execute_script("arguments[0].click();", incomplete_task)
            
            # Wait for task to load
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.question-content"))
            )
            
            self.log("Navigated to first incomplete task successfully")
            return True

        except Exception as e:
            self.log(f"Task selection failed: {str(e)}", error=True)
            return False

    def solving_loop(self):
        """Main solving process loop"""
        while self.is_running:
            try:
                # Handle different question types
                if self.is_bookwork_check():
                    self.handle_bookwork_check()
                else:
                    self.handle_normal_question()
                
                # Navigate to next question
                self.navigate_next()
                
            except Exception as e:
                self.log(f"Solving error: {str(e)}", error=True)
                if not self.recover_session():
                    break

    def handle_normal_question(self):
        """Process regular math questions"""
        image_path = self.capture_question_image()
        self.display_question_image(image_path)
        
        question_id = self.generate_question_id(image_path)
        if question_id in self.answers_db:
            answer = self.answers_db[question_id]
        else:
            answer = self.solve_with_ai(image_path)
            self.cache_answer(question_id, answer)
            
        self.submit_answer(answer)

    def handle_bookwork_check(self):
        """Handle special Bookwork check questions"""
        bookwork_code = self.extract_bookwork_code()
        self.log(f"Bookwork check detected: {bookwork_code}")
        
        if bookwork_code in self.answers_db:
            answer = self.answers_db[bookwork_code]
            self.select_bookwork_answer(answer)
            self.submit_bookwork_answer()
        else:
            image_path = self.capture_question_image()
            answer = self.solve_with_ai(image_path)
            self.cache_answer(bookwork_code, answer)
            self.select_bookwork_answer(answer)
            self.submit_bookwork_answer()

    # Browser operations
    def initialize_browser(self):
        """Set up Chrome browser with automation settings"""
        self.log("Initializing browser...")
        chrome_options = Options()
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        
        try:
            self.driver = webdriver.Chrome(
                service=Service(ChromeDriverManager().install()),
                options=chrome_options
            )
            self.driver.implicitly_wait(10)
        except Exception as e:
            self.log(f"Browser initialization failed: {str(e)}", error=True)
            raise

    def login_to_sparx(self, username, password):
        """Handle Sparx login process"""
        self.log("Navigating to Sparx Maths...")
        self.driver.get("https://www.sparxmaths.uk/student")
        
        # Handle cookie consent
        try:
            self.click_element("button#cookie-accept", timeout=3)
        except (NoSuchElementException, TimeoutException):
            pass
        
        # Human-like typing simulation
        self.human_type("input#username", username)
        self.human_type("input#password", password + Keys.RETURN)
        
        # Verify successful login
        try:
            WebDriverWait(self.driver, 15).until(
                lambda d: "login" not in d.current_url.lower()
            )
            self.log("Login successful")
        except TimeoutException:
            raise Exception("Login failed - check credentials")

    # Image processing and AI solution
    def capture_question_image(self):
        """Capture and preprocess question image"""
        try:
            question_area = self.find_element_with_fallback([
                "div[data-testid='question-container']",
                "div.question-content",
                "div.math-problem-wrapper"
            ])
            
            self.driver.save_screenshot("full_page.png")
            img = Image.open("full_page.png")
            
            loc = question_area.location
            size = question_area.size
            crop_box = (
                loc['x'], loc['y'],
                loc['x'] + size['width'],
                loc['y'] + size['height']
            )
            
            cropped_img = img.crop(crop_box)
            filename = f"question_{int(time.time())}.png"
            cropped_img.save(filename)
            
            return filename
        except Exception as e:
            self.log(f"Image capture failed: {str(e)}", error=True)
            raise

    def preprocess_image(self, image_path):
        """Enhance image for OCR processing"""
        try:
            img = cv2.imread(image_path)
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            _, threshold = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)
            processed_path = f"processed_{os.path.basename(image_path)}"
            cv2.imwrite(processed_path, threshold)
            return processed_path
        except Exception as e:
            self.log(f"Image preprocessing failed: {str(e)}", error=True)
            return image_path

    def solve_with_ai(self, image_path):
        """Get answer from OpenAI API"""
        processed_image = self.preprocess_image(image_path)
        
        try:
            with open(processed_image, "rb") as f:
                base64_image = base64.b64encode(f.read()).decode("utf-8")
            
            openai.api_key = self.openai_entry.get() or os.getenv("OPENAI_API_KEY")
            
            response = openai.ChatCompletion.create(
                model="gpt-4-vision-preview",
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Provide only the numerical answer to this math question, rounded appropriately. Do not include any explanation."},
                        {"type": "image_url", "image_url": f"data:image/png;base64,{base64_image}"}
                    ]
                }],
                max_tokens=300
            )
            
            raw_answer = response.choices[0].message.content
            return self.clean_answer(raw_answer)
        except Exception as e:
            self.log(f"AI solution failed: {str(e)}", error=True)
            return "0"

    # Answer handling and submission
    def submit_answer(self, answer):
        """Submit answer to Sparx interface"""
        try:
            self.human_type("input.answer-input", answer)
            self.click_element("button.submit-answer")
            self.log(f"Submitted answer: {answer}")
        except NoSuchElementException:
            self.log("Using JavaScript fallback submission")
            self.driver.execute_script(f"""
                document.querySelector('input.answer-input').value = '{answer}';
                document.querySelector('button.submit-answer').click();
            """)

    # Bookwork check system
    def is_bookwork_check(self):
        """Detect Bookwork check screen"""
        try:
            return self.driver.find_element(
                By.XPATH,
                "//*[contains(text(), 'Bookwork check')]"
            ).is_displayed()
        except NoSuchElementException:
            return False

    def extract_bookwork_code(self):
        """Extract Bookwork code from page"""
        try:
            element = self.driver.find_element(
                By.CSS_SELECTOR,
                'div[class*="BookworkCode"]'
            )
            return element.text.split()[-1].strip()
        except NoSuchElementException:
            return "UNKNOWN_CODE"

    def select_bookwork_answer(self, answer):
        """Select answer in Bookwork grid"""
        try:
            options = self.driver.find_elements(
                By.CSS_SELECTOR,
                'div.answer-option'
            )
            
            clean_answer = self.clean_answer(answer)
            for option in options:
                if self.clean_answer(option.text) == clean_answer:
                    option.click()
                    return
                    
            options[0].click()
        except Exception as e:
            self.log(f"Bookwork selection error: {str(e)}", error=True)

    def submit_bookwork_answer(self):
        """Submit Bookwork check answer"""
        try:
            self.click_element("button.bookwork-submit")
        except NoSuchElementException:
            self.driver.execute_script("""
                document.querySelector('button.bookwork-submit').click();
            """)

    # Navigation and flow control
    def navigate_next(self):
        """Progress to next question/task"""
        try:
            if self.is_task_complete():
                self.click_next_task_button()
            else:
                self.click_next_question_button()
            time.sleep(random.uniform(1.0, 2.5))
        except Exception as e:
            self.log(f"Navigation failed: {str(e)}", error=True)

    def is_task_complete(self):
        """Check if current task is completed"""
        try:
            return self.driver.find_element(
                By.CSS_SELECTOR,
                "div.task-complete-indicator"
            ).is_displayed()
        except NoSuchElementException:
            return False

    def click_next_question_button(self):
        """Navigate to next question"""
        try:
            self.click_element("button.next-question")
        except NoSuchElementException:
            self.driver.execute_script("""
                document.querySelector('button.next-question').click();
            """)

    def click_next_task_button(self):
        """Navigate to next task package"""
        try:
            self.click_element('a.next-task-link')
        except NoSuchElementException:
            self.driver.execute_script("""
                document.querySelector('a.next-task-link').click();
            """)

    # Utility functions
    def clean_answer(self, text):
        """Normalize answer text for comparison"""
        return (
            text.strip()
            .lower()
            .replace("answer:", "")
            .replace("answer is", "")
            .replace(" ", "")
            .replace("cm", "")
            .replace(")", "")
            .replace(",", ".")
        )

    def generate_question_id(self, image_path):
        """Create unique question identifier"""
        with open(image_path, "rb") as f:
            return hashlib.md5(f.read()).hexdigest()[:12]

    def cache_answer(self, identifier, answer):
        """Store answer in local database"""
        self.answers_db[identifier] = answer
        self.save_answers()

    def human_type(self, selector, text):
        """Simulate human typing patterns"""
        element = self.driver.find_element(By.CSS_SELECTOR, selector)
        actions = ActionChains(self.driver)
        actions.move_to_element(element).click()
        
        for char in text:
            actions.send_keys(char)
            actions.pause(random.uniform(0.1, 0.4))
        actions.perform()

    def click_element(self, selector, timeout=10):
        """Reliable element clicking with wait"""
        element = WebDriverWait(self.driver, timeout).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
        )
        element.click()

    def find_element_with_fallback(self, selectors):
        """Find element with multiple selector options"""
        for selector in selectors:
            try:
                return self.driver.find_element(By.CSS_SELECTOR, selector)
            except NoSuchElementException:
                continue
        raise NoSuchElementException(f"No elements found with selectors: {selectors}")

    # Session management
    def recover_session(self):
        """Attempt to recover from errors"""
        try:
            self.driver.refresh()
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.question-content"))
            )
            return True
        except Exception as e:
            self.log(f"Recovery failed: {str(e)}", error=True)
            return False

    # Data persistence
    def load_answers(self):
        """Load answer database from file"""
        try:
            if os.path.exists("answers.json"):
                with open("answers.json", "r") as f:
                    self.answers_db = json.load(f)
                self.log("Loaded previous answers database")
        except Exception as e:
            self.log(f"Load error: {str(e)}", error=True)

    def save_answers(self):
        """Save answer database to file"""
        try:
            with open("answers.json", "w") as f:
                json.dump(self.answers_db, f, indent=2)
        except Exception as e:
            self.log(f"Save error: {str(e)}", error=True)

    # UI management
    def display_question_image(self, image_path):
        """Update UI with current question image"""
        try:
            img = Image.open(image_path)
            img.thumbnail((1100, 550))
            self.current_question_image = ImageTk.PhotoImage(img)
            self.question_canvas.create_image(0, 0, anchor=tk.NW, image=self.current_question_image)
            self.root.update()
        except Exception as e:
            self.log(f"Image display error: {str(e)}", error=True)

    def log(self, message, error=False):
        """Update log system with timestamp"""
        tag = "[ERROR]" if error else "[INFO]"
        self.log_text.insert(tk.END, f"{time.strftime('%H:%M:%S')} {tag} {message}\n")
        self.log_text.see(tk.END)
        self.status_var.set(message[:70])
        self.root.update()

    def toggle_controls(self):
        """Update UI control states"""
        state = tk.NORMAL if not self.is_running else tk.DISABLED
        self.start_btn.config(state=state)
        self.stop_btn.config(state=tk.NORMAL if self.is_running else tk.DISABLED)

    def stop_solver(self):
        """Clean shutdown procedure"""
        self.is_running = False
        self.toggle_controls()
        self.save_answers()
        
        try:
            if self.driver:
                self.driver.quit()
        except Exception as e:
            self.log(f"Shutdown error: {str(e)}", error=True)
        
        self.log("Solver stopped successfully")
        self.root.update()

if __name__ == "__main__":
    root = tk.Tk()
    app = SparxMathsSolver(root)
    root.mainloop()