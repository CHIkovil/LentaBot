import pytest
from . import conf
from store import save_new_listen_channels_to_common_collection, STORAGE

_db_name = conf.APP_NAME + 'Test'
_element_len = 4


@pytest.mark.asyncio
async def test_save_new_listen_channels_to_common_collection():
    client = await STORAGE.get_client()
    db = client[_db_name]

    channels = {i: 'username' for i in range(0, _element_len)}
    await save_new_listen_channels_to_common_collection(channels=channels,
                                                        user_id=1,
                                                        db_name=_db_name)

    assert (conf.LISTEN_CHANNELS_COLL_NAME in list(await db.list_collection_names())) == True
    assert len([obj async for obj in db[conf.LISTEN_CHANNELS_COLL_NAME].find({})]) == _element_len

    await save_new_listen_channels_to_common_collection(channels=channels,
                                                        user_id=2,
                                                        db_name=_db_name)

    assert len([obj async for obj in db[conf.LISTEN_CHANNELS_COLL_NAME].find({})]) == _element_len

    channels = {i: "username" for i in range(_element_len, _element_len + 4)}
    await save_new_listen_channels_to_common_collection(channels=channels,
                                                        user_id=2,
                                                        db_name=_db_name)

    assert len([obj async for obj in db[conf.LISTEN_CHANNELS_COLL_NAME].find({})]) == _element_len * 2

    await client.drop_database(_db_name)
