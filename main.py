import asyncio
import sqlite3

from pywebio import start_server
from pywebio.input import *
from pywebio.output import *
from pywebio.session import run_async, run_js

# Init DataBase
db = sqlite3.connect('atom.db')
sql = db.cursor()

# Create Table
sql.execute("""CREATE TABLE IF NOT EXISTS chat (msgs TEXT)""")
sql.execute("""CREATE TABLE IF NOT EXISTS users (nickname TEXT, password TEXT)""")
db.commit()

sql.execute(f"SELECT * FROM chat")
if sql.fetchone() is None:
    sql.execute("""INSERT INTO chat (msgs) VALUES ("[]")""")
    db.commit()


sql.execute(f"SELECT * FROM users")
if sql.fetchone() is None:
    sql.execute("INSERT INTO users VALUES (?, ?)", ('VIP', 'vipip'))
    db.commit()


def chat_msgs() -> list:
    sql.execute(f"SELECT * FROM chat")
    result = sql.fetchone()
    if result[0] == "[]":
        return []
    else:
        return eval(result[0])


def check(n) -> bool:
    nickname = str(n["nickname"])
    password = str(n['password'])
    if nickname == '📢':
        return True
    sql.execute(f"SELECT nickname FROM users WHERE nickname = '{nickname}'")
    if sql.fetchone() is None:
        sql.execute("INSERT INTO users VALUES (?, ?)", (nickname, password))
        db.commit()
        return False
    else:
        sql.execute(f"SELECT * FROM users WHERE nickname = '{nickname}'")
        result = sql.fetchone()
        if result[0] == nickname and result[1] == password:
            print(f'nickname: {nickname}, password: {password}')
            return False
        else:
            return True


MAX_MESSAGES_COUNT = 100


async def main():
    put_markdown("## 🧊 Добро пожаловать в онлайн чат!\n")

    msg_box = output()
    put_scrollable(msg_box, height=300, keep_bottom=True)

    data = await input_group("Войти или Зарегестрироваться",
                             [
                                 input(required=True, name="nickname", placeholder="Ваше имя"),
                                 input(required=True, name="password", placeholder="Ваше пароль", type="password")
                             ],
                             validate=lambda n: {"error", "Упс! что то не так проверь данные..."} if check(n) else None
                             )
    nickname = data["nickname"]

    result = chat_msgs()
    result.append(f'{nickname} присоединился к чату!')
    sql.execute("""UPDATE chat SET msgs = \"{}\"""".format(str(result)))
    db.commit()
    msg_box.append(put_markdown(f'{nickname} присоединился к чату'))

    refresh_task = run_async(refresh_msg(nickname, msg_box))

    while True:
        data = await input_group("Новое сообщение", [
            input(placeholder="Текст сообщения ...", name="msg"),
            actions(name="cmd", buttons=["Отправить", {'label': "Выйти из чата", 'type': 'cancel'}])
        ], validate=lambda m: ('msg', "Введите текст сообщения!") if m["cmd"] == "Отправить" and not m['msg'] else None)

        if data is None:
            break

        msg_box.append(put_markdown(f"{nickname}: {data['msg']}"))
        result = chat_msgs()
        result.append((nickname, data['msg']))
        sql.execute("""UPDATE chat SET msgs = \"{}\"""".format(str(result)))
        db.commit()

    refresh_task.close()

    toast("Вы вышли из чата!")
    msg_box.append(put_markdown(f' Пользователь {nickname} покинул чат!'))
    result = chat_msgs()
    result.append(f'Пользователь {nickname} покинул чат!')
    sql.execute("""UPDATE chat SET msgs = \"{}\"""".format(str(result)))
    db.commit()

    put_buttons(['Перезайти'], onclick=lambda btn: run_js('window.location.reload()'))


async def refresh_msg(nickname, msg_box):
    last_idx = len(chat_msgs())

    while True:
        await asyncio.sleep(1)

        for m in chat_msgs()[last_idx:]:
            if m[0] != nickname:  # if not a message from current user
                msg_box.append(put_markdown(f"{m[0]}: {m[1]}"))

        # remove expired
        if len(chat_msgs()) > MAX_MESSAGES_COUNT:
            result = chat_msgs()[len(chat_msgs()) // 2:]
            sql.execute("""UPDATE chat SET msgs = \"{}\"""".format(str(result)))
            db.commit()

        last_idx = len(chat_msgs())


if __name__ == "__main__":
    start_server(main, debug=True, port=29295, cdn=False)