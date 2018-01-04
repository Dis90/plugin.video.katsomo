# -*- coding: utf-8 -*-

import sys
from urlparse import parse_qsl
import json

from resources.lib.kodihelper import KodiHelper

base_url = sys.argv[0]
handle = int(sys.argv[1])
helper = KodiHelper(base_url, handle)

def list_pages():
    helper.add_item('Kaikki ohjelmat', params={'action': 'list_programs', 'category': 'all'})
    helper.add_item('Kategoriat', params={'action': 'list_categories'})
    helper.add_item('Live TV', params={'action': 'livetv'})
    helper.add_item('Oma kanava', params={'action': 'favorites'})
    helper.add_item('Haku', params={'action': 'search'})  # search
    helper.eod()

def list_programs(category=None):
    programs = helper.k.get_programs()
    for program in programs:
        if category:
            if program['parentWonName'].encode('utf-8') == category:
                title = program['title'].encode('utf-8')
                params = {
                    'action': 'list_videos_or_subcats',
                    'program_id': program['id']
                }

                helper.add_item(title, params)
        else:
                title = program['title'].encode('utf-8')
                params = {
                    'action': 'list_videos_or_subcats',
                    'program_id': program['id']
                }

                helper.add_item(title, params)
    helper.eod()

def list_categories():
    helper.add_item('Dokumentit ja asiaohjelmat', params={'action': 'list_programs', 'category': 'Dokumentit ja asiaohjelmat'})
    helper.add_item('Elokuvat', params={'action': 'list_programs', 'category': 'Elokuvat'})
    helper.add_item('Kotimaiset sarjat', params={'action': 'list_programs', 'category': 'Kotimaiset sarjat'})
    helper.add_item('Lastenohjelmat', params={'action': 'list_programs', 'category': 'Lastenohjelmat'})
    helper.add_item('Muut', params={'action': 'list_programs', 'category': 'Muut'})
    helper.add_item('Ulkomaiset sarjat', params={'action': 'list_programs', 'category': 'Ulkomaiset sarjat'})
    helper.add_item('Urheilu', params={'action': 'list_programs', 'category': 'Urheilu'})
    helper.add_item('Uutiset ja sää', params={'action': 'list_programs', 'category': 'Uutiset ja sää'})
    helper.eod()

def list_favorites():
    favorites = helper.k.get_favorites()
    for favorite in favorites['favorites']:
        #Get names of the programs
        title = helper.k.get_program_name_by_id(favorite['programCategoryId'])
        params = {
            'action': 'list_videos_or_subcats',
            'program_id': favorite['programCategoryId']
        }

        helper.add_item(title, params)
    helper.eod()

def list_videos_or_subcats(program_id):
    subcats = helper.k.get_subcats(program_id)
    if subcats['numberOfHits'] > 1:
        list_subcats(program_id, subcats)
    else:
        list_videos(program_id=program_id)

def list_subcats(program_id, subcats):
    for subcat in subcats['category']:
        #Get amount of videos from subcategory for hiding them if category is empty (maybe there's better way to check this, this method is kinda slow)
        videos = helper.k.get_videos(program_id, subcat['@id'])
        #List only subcategories where is more than 0 videos
        if videos['numberOfHits'] > 0:
            title = subcat['title']
            params = {
                'action': 'list_videos',
                'program_id': program_id,
                'subcat_id': subcat['@id']
            }
            helper.add_item(title, params)
    helper.eod()

def list_videos(program_id=None, subcat_id=None, search_query=None, series_data=None):
    if program_id or subcat_id:
        videos_data = helper.k.get_videos(program_id, subcat_id)
        if videos_data['numberOfHits'] > 1:
            videos = videos_data['asset']
        else:
            videos = []
            videos.append(videos_data['asset'])
    else:
        videos = helper.k.get_search_data(search_query)['asset']

    for i in videos:
        params = {
            'action': 'play',
            'video_id': i['@id']
        }

        episode_info = {
            'mediatype': 'episode',
            'title': i.get('subtitle'),
            'tvshowtitle': i.get('title'),
            'plot': i.get('description'),
            'duration': i.get('duration'),
            'aired': i.get('liveBroadcastTime')
        }

        fanart_image = helper.k.get_program_fanart(program_id) if not search_query else None
        thumb_image = i['imageVersions']['image']['url'] if i['imageVersions'] else None

        episode_art = {
            'fanart': fanart_image,
            'thumb': thumb_image
        }

        helper.add_item(i.get('subtitle'), params=params, info=episode_info, art=episode_art, content='episodes', playable=True)
    helper.eod()

def list_channels():
    channels = helper.k.get_videos(33100, subcat_id=None)
    for i in channels['asset']:
        params = {
            'action': 'play',
            'video_id': i['@id']
        }

        episode_info = {
            'mediatype': 'episode',
            'title': i.get('title'),
            'plot': i.get('description'),
            'duration': i.get('duration')
        }

        episode_art = {
            'thumb': i['imageVersions']['image']['url']
        }

        helper.add_item(i.get('title'), params=params, info=episode_info, art=episode_art, content='episodes', playable=True)
    helper.eod()

def search():
    search_query = helper.get_user_input('Hakusana')
    if search_query:
        list_videos(search_query=search_query)
    else:
        helper.log('No search query provided.')
        return False

def router(paramstring):
    """
    Router function that calls other functions
    depending on the provided paramstring
    :param paramstring: URL encoded plugin paramstring
    :type paramstring: str
    """
    # Parse a URL-encoded paramstring to the dictionary of
    # {<parameter>: <value>} elements
    params = dict(parse_qsl(paramstring))
    # Check the parameters passed to the plugin
    if 'setting' in params:
        if params['setting'] == 'reset_credentials':
            helper.reset_credentials()
    elif 'action' in params:
        if params['action'] == 'list_programs':
            if params['category'] == 'all':
                list_programs()
            else:
                list_programs(category=params['category'])
        elif params['action'] == 'list_categories':
            list_categories()
        elif params['action'] == 'favorites':
            list_favorites()
        elif params['action'] == 'livetv':
            list_channels()
        elif params['action'] == 'list_videos_or_subcats':
            list_videos_or_subcats(params['program_id'])
        elif params['action'] == 'list_videos':
            list_videos(program_id=params['program_id'], subcat_id=params['subcat_id'])
        elif params['action'] == 'play':
            # Play a video from a provided URL.
            helper.play_item(params['video_id'])
        elif params['action'] == 'search':
            search()
    else:
        if helper.check_for_prerequisites():
            try:
                helper.login_process() # Have to trigger login process every time to get new cookie
                # If the plugin is called from Kodi UI without any parameters,
                # display the list of video categories
                list_pages()
            except helper.k.KatsomoError as error:
                if error.value == 'AUTHENTICATION_FAILED':
                    helper.dialog('ok', 'Error', error.value)

if __name__ == '__main__':
    # Call the router function and pass the plugin call parameters to it.
    # We use string slicing to trim the leading '?' from the plugin call paramstring
    router(sys.argv[2][1:])
