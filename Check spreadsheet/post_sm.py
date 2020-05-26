import os

import requests
import telegram
import vk_api


def post_vkontakte(image_path, text):
    vk, upload = customize_vk_api()
    vk_group_id = os.getenv('VK_GROUP_ID')
    if text and image_path:
        photo_id = vk_upload_photo(upload, image_path, vk_group_id)
        photo_name = f'photo-{vk_group_id}_{photo_id}'
        vk.wall.post(owner_id=f'-{vk_group_id}', message=text, attachments=photo_name)
    elif text and not image_path:
        vk.wall.post(owner_id=f'-{vk_group_id}', message=text)
    else:
        photo_id = vk_upload_photo(upload, image_path, vk_group_id)
        photo_name = f'photo-{vk_group_id}_{photo_id}'
        vk.wall.post(owner_id=f'-{vk_group_id}', attachments=photo_name)


def customize_vk_api():
    vk_access_token = os.getenv('VK_ACCESS_TOKEN')
    vk_api_version = '5.101'
    vk_session = vk_api.VkApi(token=vk_access_token, api_version=vk_api_version)
    vk = vk_session.get_api()
    upload = vk_api.VkUpload(vk_session)
    return vk, upload


def vk_upload_photo(upload, image_path, vk_group_id):
    vk_album_id = os.getenv('VK_ALBUM_ID')
    photo_info = upload.photo(
        image_path,
        album_id=vk_album_id,
        group_id=vk_group_id
        )
    photo_id = photo_info[0]['id']
    return photo_id


def post_telegram(image_path, text):
    tg_bot_token = os.getenv('TG_BOT_TOKEN')
    chat_url = os.getenv('TG_CHAT_URL')
    bot = telegram.Bot(token=tg_bot_token)
    if text:
        bot.send_message(chat_id=chat_url, text=text)
    if image_path:
        with open(image_path, 'rb') as photo:
            bot.send_photo(chat_id=chat_url, photo=photo)


def post_facebook(image_path, text):
    fb_group_id = os.getenv('FB_GROUP_ID')
    fb_token = os.getenv('FB_TOKEN')
    url = f'https://graph.facebook.com/{fb_group_id}/photos'
    payload = {'access_token': fb_token}
    if text:
        payload.update({'caption': text})
    if image_path:
        with open(image_path, 'rb') as photo:
            files = {'file': photo}
            response = requests.post(url, files=files, params=payload)
    else:
        response = requests.post(url, params=payload)
    response.raise_for_status()
