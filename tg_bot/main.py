import logging
import re
import paramiko
import asyncpg

from dotenv import load_dotenv
import os

# Загружаем переменные окружения из .env файла
load_dotenv()

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ForceReply, Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters, ConversationHandler, CallbackQueryHandler, CallbackContext



TOKEN = os.getenv("TOKEN")
rm_host = os.getenv("RM_HOST")
rm_port = os.getenv("RM_PORT")
rm_user = os.getenv("RM_USER")
rm_password = os.getenv("RM_PASSWORD")

db_user = os.getenv("DB_USER")
db_password = os.getenv("DB_PASSWORD")
db_host = os.getenv("DB_HOST")
db_port = int(os.getenv("DB_PORT"))
db_database = os.getenv("DB_DATABASE")


# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO, filename='myProgramLog.txt'
)
# set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

SEARCHING, CONFIRMING_EMAIL, CONFIRMING_NUMBER = range(3)

MAX_MESSAGE_LENGTH = 4096

async def send_long_message(bot, chat_id: int, text: str) -> None:
    """Отправка длинного сообщения, разбивая его на части."""
    for i in range(0, len(text), MAX_MESSAGE_LENGTH):
        await bot.send_message(chat_id=chat_id, text=text[i:i + MAX_MESSAGE_LENGTH])

# Define a few command handlers. These usually take the two arguments update and
# context.
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    user = update.effective_user
    await update.message.reply_html(
        rf"Привет {user.mention_html()}!",
        # reply_markup=ForceReply(selective=True),
    )
async def findPhoneNumbersCommand(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text('Введите текст для поиска адресов электронной почты: ')

    return 'findPhoneNumbers'

async def find_phone_numbers(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_input = update.message.text  # Получаем текст от пользователя

    phone_num_regex = re.compile(r'(?:\+7|8)[\s-]?(?:\(?\d{3}\)?)[\s-]?\d{3}[\s-]?\d{2}[\s-]?\d{2}')  # Формат номеров
    phone_number_list = phone_num_regex.findall(user_input)  # Ищем номера телефонов

    if not phone_number_list:  # Если номера не найдены
        await update.message.reply_text('Телефонные номера не найдены.')
        return ConversationHandler.END  # Завершаем диалог

    # Формируем сообщение с найденными номерами
    phone_numbers = '\n'.join(f'{i + 1}. {num}' for i, num in enumerate(phone_number_list))
    await update.message.reply_text(f'Найдены следующие номера:\n{phone_numbers}\n\nХотите добавить их в базу данных? (да/нет)')

    # Сохраняем найденные номера в контексте для дальнейшего использования
    context.user_data['found_numbers'] = phone_number_list

    return CONFIRMING_NUMBER  # Переход к следующему состоянию

# Функция для обработки подтверждения сохранения номеров в БД
async def confirm_add_number(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_response = update.message.text.lower()  # Получаем ответ пользователя

    if user_response == 'да':
        phone_numbers = context.user_data.get('found_numbers', [])
        for number in phone_numbers:
            await add_number(update, context, number)  # Сохраняем каждый номер в БД

        await update.message.reply_text('Все номера успешно добавлены в базу данных!')
    elif user_response == 'нет':
        await update.message.reply_text('Запись отменена.')
    else:
        await update.message.reply_text('Пожалуйста, ответьте "да" или "нет".')
        return CONFIRMING_NUMBER  # Ожидаем корректный ответ

    return ConversationHandler.END  # Завершаем диалог

# Функция для добавления номера в базу данных
async def add_number(update: Update, context: CallbackContext, number: str) -> None:
    try:
        conn = await connect_db()
        await conn.execute("INSERT INTO number (number) VALUES ($1)", number)
        await conn.close()

        logger.info(f'Число {number} успешно добавлено!')
    except Exception as e:
        logger.error(f'Ошибка при добавлении числа {number}: {e}')
        await update.message.reply_text(f'Произошла ошибка при добавлении числа {number}.')






async def findEmailsCommand(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text('Введите текст для поиска адресов электронной почты: ')

    return 'findEmails'


async def findEmails(update: Update, context):
    user_input = update.message.text  # Получаем текст от пользователя

    emailsRegex = re.compile(
        r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.(?:ru|com)')  # Формат номеров
    emailsList = emailsRegex.findall(user_input)  # Ищем номера телефонов

    if not emailsList:
        await update.message.reply_text('Ни один адрес электронной почты не был найден')
        return ConversationHandler.END  # Завершаем диалог


    emails = '\n'.join(f'{i + 1}. {num}' for i, num in enumerate(emailsList))

    # Формируем сообщение с найденными номерами

    await update.message.reply_text(
        f'Найдены следующие номера:\n{emails}\n\nХотите добавить их в базу данных? (да/нет)')

    # Сохраняем найденные номера в контексте для дальнейшего использования
    context.user_data['found_emails'] = emailsList

    return CONFIRMING_EMAIL  # Переход к следующему состоянию

async def confirm_add_email(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_response = update.message.text.lower()  # Получаем ответ пользователя

    if user_response == 'да':
        emails = context.user_data.get('found_emails', [])
        for email in emails:
            await add_email(update, context, email)  # Сохраняем каждый номер в БД

        await update.message.reply_text('Все email успешно добавлены в базу данных!')
    elif user_response == 'нет':
        await update.message.reply_text('Запись отменена.')
    else:
        await update.message.reply_text('Пожалуйста, ответьте "да" или "нет".')
        return CONFIRMING_EMAIL  # Ожидаем корректный ответ

    return ConversationHandler.END  # Завершаем диалог

async def add_email(update: Update, context: CallbackContext, email: str) -> None:
    try:
        conn = await connect_db()
        await conn.execute("INSERT INTO email (email) VALUES ($1)", email)
        await conn.close()

        logger.info(f'Email {email} успешно добавлено!')
    except Exception as e:
        logger.error(f'Ошибка при добавлении email {email}: {e}')
        await update.message.reply_text(f'Произошла ошибка при добавлении email {email}.')


async def verifyPasswordCommand(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text('Введите пароль: ')

    return 'verifyPassword'


async def verifyPassword(update: Update, context):
    user_input = update.message.text

    passwordRegex = re.compile(r'^(?=.*[A-Z])(?=.*[a-z])(?=.*\d)(?=.*[!@#$%^&*()])[A-Za-z\d!@#$%^&*()]{8,}$')

    passwordVerify = passwordRegex.match(user_input)

    if not passwordVerify:
        await update.message.reply_text('Пароль простой')

    if passwordVerify:
        await update.message.reply_text('Пароль сложный')

    return ConversationHandler.END


async def execute_command(command: str) -> str:
    """Выполняет указанную команду на удалённом хосте."""
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(hostname=rm_host, username=rm_user, password=rm_password, port=rm_port)

    stdin, stdout, stderr = client.exec_command(command)
    data = stdout.read() + stderr.read()
    client.close()

    return data.decode('utf-8')

async def get_release(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:

    result = await execute_command('uname -r')
    await update.message.reply_text(result)


async def get_uname(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:

    result = await execute_command('uname -pvn')
    await update.message.reply_text(result)

async def get_uptime(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:

    result = await execute_command('uptime')
    await update.message.reply_text(result)

async def get_df(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:

    result = await execute_command('df')
    await update.message.reply_text(result)

async def get_free(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:

    result = await execute_command('free')
    await update.message.reply_text(result)

async def get_mpstat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:

    result = await execute_command('mpstat')
    await update.message.reply_text(result)

async def get_w(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:

    result = await execute_command('w')
    await update.message.reply_text(result)

async def get_ps(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:

    result = await execute_command('ps')
    await update.message.reply_text(result)


async def get_ss(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:

    result = await execute_command('ss')
    await update.message.reply_text(result)

async def get_services(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:

    result = await execute_command('systemctl list-units --type=services --state=running')
    await update.message.reply_text(result)

async def get_repl_logs(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(hostname=db_host, username=db_user, password=db_password, port=rm_port)
    stdin, stdout, stderr = client.exec_command('cat /var/log/postgresql/postgresql.log | grep -C 3 -i repl')
    data = stdout.read() + stderr.read()
    client.close()
    result = data.decode('utf-8')
    await send_long_message(context.bot, update.message.chat_id, result)


async def get_apt_listCommand(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Вы хотите:\n1. Вывести все пакеты (введите 1)\n2. Найти пакет по названию (введите 2)"
    )

    return 'get_apt_list'

async def handle_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_choice = update.message.text

    if user_choice == "1":
        result = await execute_command('apt list --installed')
        await send_long_message(context.bot, update.message.chat_id, result)


    elif user_choice == "2":
        await update.message.reply_text("Введите название пакета:")


    return 'handle_package_name'

async def handle_package_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    package_name = update.message.text

    logger.info(f"User {update.effective_user.id} is searching for package: {package_name}")

    result = await execute_command(f'apt show {package_name}')

    if result:
        await send_long_message(context.bot, update.message.chat_id, result)
    else:
        await update.message.reply_text("Пакет не найден.")


    return ConversationHandler.END  # Завершаем работу обработчика диалога






async def connect_db():
    try:
        logger.info("Попытка подключения к базе данных...")
        connection = await asyncpg.connect(
            database=db_database,  # Имя базы данных
            user=db_user,  # Имя пользователя
            password=db_password,  # Пароль
            host=db_host,  # Или IP-адрес вашего сервера
            port=db_port  # Порт, если отличается от стандартного

        )
        logger.info("Успешно подключено к базе данных.")
        return connection
    except Exception as e:
        logger.error(f"Ошибка при подключении к базе данных: {e}")
        raise  # Перебрасываем исключение дальше, чтобы его можно было обработать в вызывающем коде






# Команда для получения всех данных из таблицы
async def get_numbers(update: Update, context: CallbackContext) -> None:
    try:
        logger.info("Попытка подключения к базе данных для получения чисел...")
        conn = await connect_db()
        logger.info("Успешно подключено к базе данных.")

        logger.info("Выполнение запроса к базе данных...")
        rows = await conn.fetch("SELECT * FROM number")
        logger.info(f"Запрос выполнен. Получено {len(rows)} записей.")

        await conn.close()

        if rows:
            result = "\n".join([f"ID: {row['id']}, Number: {row['number']}" for row in rows])
            await update.message.reply_text(f'Данные из БД:\n{result}')
        else:
            await update.message.reply_text('Таблица пуста.')
    except Exception as e:
        logger.error(f'Ошибка при получении данных: {e}')
        await update.message.reply_text('Произошла ошибка при получении данных.')





# Команда для получения всех данных из таблицы
async def get_emails(update: Update, context: CallbackContext) -> None:
    try:
        logger.info("Попытка подключения к базе данных для получения чисел...")
        conn = await connect_db()
        logger.info("Успешно подключено к базе данных.")

        logger.info("Выполнение запроса к базе данных...")
        rows = await conn.fetch("SELECT * FROM email")
        logger.info(f"Запрос выполнен. Получено {len(rows)} записей.")

        await conn.close()

        if rows:
            result = "\n".join([f"ID: {row['id']}, Email: {row['email']}" for row in rows])
            await update.message.reply_text(f'Данные из БД:\n{result}')
        else:
            await update.message.reply_text('Таблица пуста.')
    except Exception as e:
        logger.error(f'Ошибка при получении данных: {e}')
        await update.message.reply_text('Произошла ошибка при получении данных.')


def main() -> None:
    """Start the bot."""
    # Create the Application and pass it your bot's token.
    application = Application.builder().token(TOKEN).build()

    convHandlerFindEmails = ConversationHandler(
        entry_points=[CommandHandler('find_email', findEmailsCommand)],
        states={
            'findEmails': [MessageHandler(filters.TEXT & ~filters.COMMAND, findEmails)],
            CONFIRMING_EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_add_email)],
        },
        fallbacks=[]
    )

    convHandlerFindPhoneNumbers = ConversationHandler(
        entry_points=[CommandHandler('find_numbers', findPhoneNumbersCommand)],
        states={
            'findPhoneNumbers': [MessageHandler(filters.TEXT & ~filters.COMMAND, find_phone_numbers)],
            CONFIRMING_NUMBER: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_add_number)],
        },
        fallbacks=[],
    )

    convHandlerVerifyPassword = ConversationHandler(
        entry_points=[CommandHandler('verifyPassword', verifyPasswordCommand)],
        states={
            'verifyPassword': [MessageHandler(filters.TEXT & ~filters.COMMAND, verifyPassword)],
        },
        fallbacks=[]
    )

    convHandler_apt_list = ConversationHandler(
        entry_points=[CommandHandler('get_apt_list', get_apt_listCommand)],
        states={
            'get_apt_list': [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_choice)],
            'handle_package_name': [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_package_name)]
        },
        fallbacks=[]
    )





    # on different commands - answer in Telegram
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("get_release", get_release))
    application.add_handler(CommandHandler("get_uname", get_uname))
    application.add_handler(CommandHandler("get_df", get_df))
    application.add_handler(CommandHandler("get_uptime", get_uptime))
    application.add_handler(CommandHandler("get_free", get_free))
    application.add_handler(CommandHandler("get_mpstat", get_mpstat))
    application.add_handler(CommandHandler("get_w", get_w))
    application.add_handler(CommandHandler("get_ps", get_ps))
    application.add_handler(CommandHandler("get_ss", get_ss))
    application.add_handler(CommandHandler("get_services", get_services))
    application.add_handler(CommandHandler("get_numbers", get_numbers))
    application.add_handler(CommandHandler("get_emails", get_emails))
    application.add_handler(CommandHandler("get_repl_logs", get_repl_logs))
    application.add_handler(convHandlerFindPhoneNumbers)
    application.add_handler(convHandlerFindEmails)
    application.add_handler(convHandlerVerifyPassword)
    application.add_handler(convHandler_apt_list)

    # Run the bot until the user presses Ctrl-C
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
