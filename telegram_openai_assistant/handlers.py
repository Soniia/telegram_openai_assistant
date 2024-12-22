import time
import datetime
from telegram.ext import CallbackContext
from telegram import Update
from openai import OpenAI

from .config import assistant_id, client_api_key
from .utils import get_message_count, update_message_count, save_qa

client = OpenAI(api_key=client_api_key)

# Diccionario para asociar usuarios con sus threads
user_threads = {}

async def start(update: Update, context: CallbackContext) -> None:
    """Sends a welcome message to the user."""
    await context.bot.send_message(
        chat_id=update.effective_chat.id, text="Hello! Ask me anything."
    )

async def help_command(update: Update, context: CallbackContext) -> None:
    """Sends a help message to the user."""
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Just send me a question and I'll try to answer it.",
    )

def get_or_create_thread(user_id):
    """Retrieve or create a thread for a user."""
    if user_id not in user_threads:
        # Crear un nuevo thread si no existe
        thread = client.beta.threads.create()
        user_threads[user_id] = thread.id
    return user_threads[user_id]

def get_answer(message_str, user_id) -> str:
    """Get answer from assistant."""
    thread_id = get_or_create_thread(user_id)

    client.beta.threads.messages.create(
        thread_id=thread_id, role="user", content=message_str
    )

    run = client.beta.threads.runs.create(
        thread_id=thread_id,
        assistant_id=assistant_id,
    )

    # Poll for the response (this could be improved with async calls)
    while True:
        run = client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)
        if run.status == "completed":
            break
        time.sleep(1)

    messages = client.beta.threads.messages.list(thread_id=thread_id)
    response = messages.dict()["data"][0]["content"][0]["text"]["value"]
    return response

async def process_message(update: Update, context: CallbackContext) -> None:
    """Processes a message from the user, gets an answer, and sends it back."""
    message_data = get_message_count()
    count = message_data["count"]
    date = message_data["date"]
    today = str(datetime.date.today())

    if date != today:
        count = 0
    if count >= 100:
        return

    user_id = update.effective_user.id
    answer = get_answer(update.message.text, user_id)
    await context.bot.send_message(chat_id=update.effective_chat.id, text=answer)
    update_message_count(count + 1)
    save_qa(
        user_id,
        update.effective_user.username,
        update.message.text,
        answer,
    )