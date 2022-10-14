from Support import *
from Support.conf import *

STORAGE = MongoStorage(db_name=MONGO_DBNAME, uri=MONGO_URL)
USER_DATA = DATA


async def delete_spam_word(keyword):
    client = await STORAGE.get_client()
    db = client[MONGO_DBNAME]
    spam_words_coll = db[SPAM_WORDS_COLL_NAME]

    exist_keywords = set(await get_all_spam_words())

    if keyword in exist_keywords:
        await spam_words_coll.delete_one({"word": {'$in': [keyword]}})
        return True
    else:
        return False


async def add_spam_word(keyword):
    client = await STORAGE.get_client()
    db = client[MONGO_DBNAME]
    spam_words_coll = db[SPAM_WORDS_COLL_NAME]

    exist_keywords = set(await get_all_spam_words())

    if keyword not in exist_keywords:
        data = {'word': keyword}
        await spam_words_coll.insert_one(data)
        return True
    else:
        return False


async def get_all_spam_words():
    client = await STORAGE.get_client()
    db = client[MONGO_DBNAME]
    spam_words_coll = db[SPAM_WORDS_COLL_NAME]

    if SPAM_WORDS_COLL_NAME in set(await db.list_collection_names()):
        return [obj['word'] async for obj in spam_words_coll.find({})]
    else:
        return []


async def get_listen_user_ids_for_channel(channel_id):
    client = await STORAGE.get_client()
    db = client[MONGO_DBNAME]
    users_coll = db[USER_DATA]

    return [obj['user'] async for obj in
            users_coll.find({"$and": [{"data.listen_channels": {'$in': [channel_id]}},
                                      {"data.is_listen": True}]})]


async def get_user_ids_with_channel_nicknames(channel_ids):
    client = await STORAGE.get_client()
    db = client[MONGO_DBNAME]
    users_coll = db[USER_DATA]
    channels_coll = db[LISTEN_CHANNELS_COLL_NAME]

    result = {}
    async for channel_obj in channels_coll.find({"id": {"$in": channel_ids}}):
        user_ids = []
        async for obj in users_coll.find({"data.listen_channels": {'$in': [channel_obj['id']]}}):
            user_ids.append(obj["user"])
        result[channel_obj['nickname']] = user_ids
    return result


async def drop_wish():
    client = await STORAGE.get_client()
    db = client[MONGO_DBNAME]
    wish_coll = db[WISH_COLL_NAME]
    await wish_coll.drop()


async def get_all_wish_texts():
    client = await STORAGE.get_client()
    db = client[MONGO_DBNAME]
    wish_coll = db[WISH_COLL_NAME]

    if WISH_COLL_NAME in set(await db.list_collection_names()):
        return [obj['text'] + '\n\n\n' async for obj in wish_coll.find({})]
    else:
        return []


async def check_exist_channel_usernames_to_store(urls, user_id):
    client = await STORAGE.get_client()
    db = client[MONGO_DBNAME]
    channels_coll = db[LISTEN_CHANNELS_COLL_NAME]

    listen_channel_nicknames = {await on_telegram_username(obj['nickname']): obj['id'] async for obj in
                                channels_coll.find({"users": {'$in': [user_id]}})}
    exist_usernames = list({await on_telegram_username(url) for url in urls} & set(listen_channel_nicknames.keys()))

    return {listen_channel_nicknames[username]: f'@{username}' for username in exist_usernames}


async def get_all_listen_users():
    client = await STORAGE.get_client()
    db = client[MONGO_DBNAME]
    users_coll = db[USER_DATA]

    return [obj async for obj in users_coll.find({"data.is_listen": True})]


async def get_all_users():
    client = await STORAGE.get_client()
    db = client[MONGO_DBNAME]
    users_coll = db[USER_DATA]

    return [obj async for obj in users_coll.find({})]


async def get_all_listen_channel_ids():
    client = await STORAGE.get_client()
    db = client[MONGO_DBNAME]
    channels_coll = db[LISTEN_CHANNELS_COLL_NAME]

    if LISTEN_CHANNELS_COLL_NAME in set(await db.list_collection_names()):
        return [obj['id'] async for obj in channels_coll.find({})]
    else:
        return None


async def save_new_listen_channels_to_common_collection(channels, user_id, db_name=MONGO_DBNAME):
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
    db = client[MONGO_DBNAME]
    channels_coll = db[LISTEN_CHANNELS_COLL_NAME]
    users_coll = db[USER_DATA]

    await channels_coll.delete_many({"id": {'$in': channel_ids}})
    await users_coll.update_many({}, {"$pull": {"data.listen_channels": {'$in': channel_ids}}})


async def delete_listen_channels_to_common_collection(channel_ids, user_id, db_name=MONGO_DBNAME):
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
    db = client[MONGO_DBNAME]
    users_coll = db[USER_DATA]

    await users_coll.update_one({"user": user_id}, {"$set": {"data.is_listen": False}})


async def get_user_wish(user_id, db_name=MONGO_DBNAME):
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


async def add_user_wish(user_id, text, db_name=MONGO_DBNAME):
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


async def on_telegram_username(url):
    tg_str = r'(@)?(https://)?(t.me/)?(\s+)?'
    return re.sub(tg_str, '', url)


async def on_telegram_url(username):
    return f'https://t.me/{username}'
