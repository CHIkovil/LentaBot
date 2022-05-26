from . import conf
from aiogram.contrib.fsm_storage.mongo import MongoStorage

STORAGE = MongoStorage(db_name=conf.APP_NAME)


async def check_channels_nickname_actuality_to_store(exist_channels):
    client = await STORAGE.get_client()
    db = client[conf.APP_NAME]
    channels_coll = db[conf.LISTEN_CHANNELS_COLL_NAME]

    exist_listen_channel = {obj['nickname']: obj['id'] async for obj in
                            channels_coll.find({"id": {"$in": list(exist_channels.keys())}})}

    not_equal_old_nicknames = list(set(exist_listen_channel.keys()) - set(exist_channels.values()))

    if not_equal_old_nicknames:
        for old_nickname in not_equal_old_nicknames:
            await channels_coll.update_one({'id': exist_listen_channel[old_nickname]},
                                           {"$set": {'nickname': exist_channels[exist_listen_channel[old_nickname]]}})


async def save_new_listen_channels_to_common_collection(channels, user_id, db_name=conf.APP_NAME):
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
    db = client[conf.APP_NAME]
    channels_coll = db[conf.LISTEN_CHANNELS_COLL_NAME]
    users_coll = db["aiogram_data"]

    await channels_coll.delete_many({"id": {'$in': channel_ids}})
    await users_coll.update_many({}, {"$pull": {"data.listen_channels": {'$in': channel_ids}}})


async def delete_listen_channels_to_common_collection(channel_ids, user_id, db_name=conf.APP_NAME):
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
    db = client[conf.APP_NAME]
    users_coll = db["aiogram_data"]

    await users_coll.update_one({"user": user_id}, {"$set": {"data.is_listen": False}})


async def drop_tape_channel_for_user(user_id):
    client = await STORAGE.get_client()
    db = client[conf.APP_NAME]
    users_coll = db["aiogram_data"]

    await stop_listen_for_user(user_id=user_id)
    await users_coll.update_one({"user": user_id}, {"$set": {"data.tape_channel": None}})


async def get_user_wish(user_id, db_name=conf.APP_NAME):
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


async def add_user_wish(user_id,text, db_name=conf.APP_NAME):
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