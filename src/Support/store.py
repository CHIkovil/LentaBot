import os
from aiogram.contrib.fsm_storage.mongo import MongoStorage

APP_NAME = os.environ.get('APP_NAME')
LISTEN_CHANNELS_COLL_NAME = os.environ.get('LISTEN_CHANNELS_COLL_NAME')
WISH_COLL_NAME = os.environ.get('WISH_COLL_NAME')

STORAGE = MongoStorage(db_name=APP_NAME)


async def get_all_listen_users():
    client = await STORAGE.get_client()
    db = client[APP_NAME]
    users_coll = db["aiogram_data"]

    return [obj async for obj in users_coll.find({"data.is_listen": True})]


async def get_all_users():
    client = await STORAGE.get_client()
    db = client[APP_NAME]
    users_coll = db["aiogram_data"]

    return [obj async for obj in users_coll.find({})]


async def get_all_listen_channel_ids():
    client = await STORAGE.get_client()
    db = client[APP_NAME]
    channels_coll = db[LISTEN_CHANNELS_COLL_NAME]

    return [obj['id'] async for obj in channels_coll.find({})]


async def check_channel_nicknames_actuality_to_common_collection(exist_channels):
    client = await STORAGE.get_client()
    db = client[APP_NAME]
    channels_coll = db[LISTEN_CHANNELS_COLL_NAME]

    exist_listen_channel = {obj['nickname']: obj['id'] async for obj in
                            channels_coll.find({"id": {"$in": list(exist_channels.keys())}})}

    not_equal_old_nicknames = list(set(exist_listen_channel.keys()) - set(exist_channels.values()))

    if not_equal_old_nicknames:
        for old_nickname in not_equal_old_nicknames:
            await channels_coll.update_one({'id': exist_listen_channel[old_nickname]},
                                           {"$set": {'nickname': exist_channels[exist_listen_channel[old_nickname]]}})


async def save_new_listen_channels_to_common_collection(channels, user_id, db_name=APP_NAME):
    client = await STORAGE.get_client()
    db = client[db_name]
    channels_coll = db[LISTEN_CHANNELS_COLL_NAME]

    if LISTEN_CHANNELS_COLL_NAME in set(await db.list_collection_names()):
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
    db = client[APP_NAME]
    channels_coll = db[LISTEN_CHANNELS_COLL_NAME]
    users_coll = db["aiogram_data"]

    await channels_coll.delete_many({"id": {'$in': channel_ids}})
    await users_coll.update_many({}, {"$pull": {"data.listen_channels": {'$in': channel_ids}}})


async def delete_listen_channels_to_common_collection(channel_ids, user_id, db_name=APP_NAME):
    client = await STORAGE.get_client()
    db = client[db_name]
    channels_coll = db[LISTEN_CHANNELS_COLL_NAME]

    for id in channel_ids:
        await channels_coll.update_one({"id": id}, {"$pull": {"users": {'$in': [user_id]}}})

    empty_users_channel_ids = [obj['id'] async for obj in channels_coll.find({"users": {"$in": [None, []]}})]

    if empty_users_channel_ids:
        channels_coll.delete_many({"id": {'$in': empty_users_channel_ids}})
        return empty_users_channel_ids


async def stop_listen_for_user(user_id):
    client = await STORAGE.get_client()
    db = client[APP_NAME]
    users_coll = db["aiogram_data"]

    await users_coll.update_one({"user": user_id}, {"$set": {"data.is_listen": False}})


async def drop_tape_channel_for_user(user_id):
    client = await STORAGE.get_client()
    db = client[APP_NAME]
    users_coll = db["aiogram_data"]

    await stop_listen_for_user(user_id=user_id)
    await users_coll.update_one({"user": user_id}, {"$set": {"data.tape_channel": None}})


async def get_user_wish(user_id, db_name=APP_NAME):
    client = await STORAGE.get_client()
    db = client[db_name]
    wish_coll = db[WISH_COLL_NAME]

    if WISH_COLL_NAME in set(await db.list_collection_names()):
        texts = [obj['text']async for obj in wish_coll.find({"user": user_id})]
        if texts:
            return texts[0]
        else:
            return None
    else:
        return None


async def add_user_wish(user_id, text, db_name=APP_NAME):
    client = await STORAGE.get_client()
    db = client[db_name]
    wish_coll = db[WISH_COLL_NAME]

    if WISH_COLL_NAME in set(await db.list_collection_names()):
        texts = [obj['text']async for obj in wish_coll.find({"user": user_id})]
        if texts:
            await wish_coll.update_one({"user": user_id}, {"$set": {"text": text}})
        else:
            data = {'user': user_id, 'text': text}
            await wish_coll.insert_one(data)
    else:
        data = {'user': user_id, 'text': text}
        await wish_coll.insert_one(data)
