import pytest
from src import conf
from src.bot import _save_new_listen_channels_to_common_collection, _STORAGE

_db_name = conf.APP_NAME + 'Test'
_element_len = 4


@pytest.mark.asyncio
async def test_save_new_listen_channels_to_common_collection():
    try:
        client = await _STORAGE.get_client()
        db = client[_db_name]

        channel_ids = [i for i in range(0, _element_len)]
        await _save_new_listen_channels_to_common_collection(channel_ids=channel_ids,
                                                             user_id=1,
                                                             db_name=_db_name)

        assert (conf.LISTEN_CHANNELS_COLL_NAME in list(await db.list_collection_names())) == True
        assert len([obj async for obj in db[conf.LISTEN_CHANNELS_COLL_NAME].find({})]) == _element_len

        await _save_new_listen_channels_to_common_collection(channel_ids=channel_ids,
                                                             user_id=2,
                                                             db_name=_db_name)

        assert len([obj async for obj in db[conf.LISTEN_CHANNELS_COLL_NAME].find({})]) == _element_len

        channel_ids = [i for i in range(_element_len, _element_len + 4)]
        await _save_new_listen_channels_to_common_collection(channel_ids=channel_ids,
                                                             user_id=2,
                                                             db_name=_db_name)

        assert len([obj async for obj in db[conf.LISTEN_CHANNELS_COLL_NAME].find({})]) == _element_len * 2
    finally:
        await client.drop_database(_db_name)
