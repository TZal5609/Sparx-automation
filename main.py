from selenium import webdriver
from selenium.webdriver.common.by import By
import openai
import sqlite3
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Access the API key
openai.api_key = os.getenv("OPENAI_API_KEY")

# Initialize SQLite database
conn = sqlite3.connect("answers.db")
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS answers (
    question TEXT PRIMARY KEY,
    answer TEXT
)
""")
conn.commit()

# Function to get answer from AI or database
def get_answer(question):
    cursor.execute("SELECT answer FROM answers WHERE question = ?", (question,))
    result = cursor.fetchone()
    if result:
        return result[0]
    else:
        # Query OpenAI API
        response = openai.Completion.create(
            engine="text-davinci-003",
            prompt=question,
            max_tokens=100
        )
        answer = response.choices[0].text.strip()
        # Store in database
        cursor.execute("INSERT INTO answers (question, answer) VALUES (?, ?)", (question, answer))
        conn.commit()
        return answer

# Selenium setup
driver = webdriver.Chrome(executable_path="path_to_chromedriver")
driver.get("https://canvas.example.com")

# Example: Locate question and answer it
question_element = driver.find_element(By.ID, "question-id")  # Adjust selector
question_text = question_element.text
answer = get_answer(question_text)

# Input the answer and continue
answer_input = driver.find_element(By.ID, "answer-input-id")  # Adjust selector
answer_input.send_keys(answer)
continue_button = driver.find_element(By.ID, "continue-button-id")  # Adjust selector
continue_button.click()

# Close resources
driver.quit()
conn.close()
