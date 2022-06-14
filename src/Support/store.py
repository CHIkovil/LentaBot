from aiogram.contrib.fsm_storage.mongo import MongoStorage
import re
from . import conf

STORAGE = MongoStorage(db_name=conf.MONGO_DBNAME, uri=conf.MONGO_URL)


async def check_exist_channel_usernames_to_store(urls, user_id):
    client = await STORAGE.get_client()
    db = client[conf.MONGO_DBNAME]
    channels_coll = db[conf.LISTEN_CHANNELS_COLL_NAME]

    listen_channel_nicknames = {await on_telegram_username(obj['nickname']): obj['id'] async for obj in channels_coll.find({"users": {'$in': [user_id]}})}
    exist_usernames = list({await on_telegram_username(url) for url in urls} & set(listen_channel_nicknames.keys()))

    return {listen_channel_nicknames[username]: f'@{username}' for username in exist_usernames}


async def get_all_listen_users():
    client = await STORAGE.get_client()
    db = client[conf.MONGO_DBNAME]
    users_coll = db["aiogram_data"]

    return [obj async for obj in users_coll.find({"data.is_listen": True})]


async def get_all_users():
    client = await STORAGE.get_client()
    db = client[conf.MONGO_DBNAME]
    users_coll = db["aiogram_data"]

    return [obj async for obj in users_coll.find({})]


async def get_all_listen_channel_ids():
    client = await STORAGE.get_client()
    db = client[conf.MONGO_DBNAME]
    channels_coll = db[conf.LISTEN_CHANNELS_COLL_NAME]

    return [obj['id'] async for obj in channels_coll.find({})]


async def save_new_listen_channels_to_common_collection(channels, user_id, db_name=conf.MONGO_DBNAME):
    client = await STORAGE.get_client()
    db = client[db_name]
    channels_coll = db[conf.LISTEN_CHANNELS_COLL_NAME]

    if conf.LISTEN_CHANNELS_COLL_NAME in set(await db.list_collection_names()):
        for id, nickname in channels.items():
            channel_obj = [obj async for obj in channels_coll.find({"id": id})]
            if channel_obj:
                await channels_coll.update_one({'id': id},
                                               {'$push': {'users': user_id}})
            else:
                await channels_coll.insert_one(
                    {'id': id, 'nickname': nickname, 'users': [user_id]})
    else:
        data = [{'id': id, 'nickname': nickname, 'users': [user_id]} for id, nickname in channels.items()]
        await channels_coll.insert_many(data)


async def delete_everywhere_listen_channels_to_store(channel_ids):
    client = await STORAGE.get_client()
    db = client[conf.MONGO_DBNAME]
    channels_coll = db[conf.LISTEN_CHANNELS_COLL_NAME]
    users_coll = db["aiogram_data"]

    await channels_coll.delete_many({"id": {'$in': channel_ids}})
    await users_coll.update_many({}, {"$pull": {"data.listen_channels": {'$in': channel_ids}}})


async def delete_listen_channels_to_common_collection(channel_ids, user_id, db_name=conf.MONGO_DBNAME):
    client = await STORAGE.get_client()
    db = client[db_name]
    channels_coll = db[conf.LISTEN_CHANNELS_COLL_NAME]

    for id in channel_ids:
        await channels_coll.update_one({"id": id}, {"$pull": {"users": {'$in': [user_id]}}})

    empty_users_channel_ids = [obj['id'] async for obj in channels_coll.find({"users": {"$in": [None, []]}})]

    if empty_users_channel_ids:
        channels_coll.delete_many({"id": {'$in': empty_users_channel_ids}})
        return empty_users_channel_ids


async def stop_listen_for_user(user_id):
    client = await STORAGE.get_client()
    db = client[conf.MONGO_DBNAME]
    users_coll = db["aiogram_data"]

    await users_coll.update_one({"user": user_id}, {"$set": {"data.is_listen": False}})


async def get_user_wish(user_id, db_name=conf.MONGO_DBNAME):
    client = await STORAGE.get_client()
    db = client[db_name]
    wish_coll = db[conf.WISH_COLL_NAME]

    if conf.WISH_COLL_NAME in set(await db.list_collection_names()):
        texts = [obj['text']async for obj in wish_coll.find({"user": user_id})]
        if texts:
            return texts[0]
        else:
            return None
    else:
        return None


async def add_user_wish(user_id, text, db_name=conf.MONGO_DBNAME):
    client = await STORAGE.get_client()
    db = client[db_name]
    wish_coll = db[conf.WISH_COLL_NAME]

    if conf.WISH_COLL_NAME in set(await db.list_collection_names()):
        texts = [obj['text']async for obj in wish_coll.find({"user": user_id})]
        if texts:
            await wish_coll.update_one({"user": user_id}, {"$set": {"text": text}})
        else:
            data = {'user': user_id, 'text': text}
            await wish_coll.insert_one(data)
    else:
        data = {'user': user_id, 'text': text}
        await wish_coll.insert_one(data)


async def on_telegram_username(url):
    tg_str = r'(@)?(https://)?(t.me/)?(\s+)?'
    return re.sub(tg_str, '', url)


async def on_telegram_url(username):
    return f'https://t.me/{username}'