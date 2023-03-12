import os
import urllib.parse
import logging
import sys
import json
import re

import requests
import arrow
import jsbeautifier
import yaml


class UnifiAPIClientException(Exception):
    pass

class UnifiAPIClient:

    _controller_url = None
    _controller_requests_session = None
    _logger = None

    all_stat_attributes = ['bytes', 'wan-tx_bytes', 'wan-rx_bytes', 'wlan_bytes', 'num_sta',
                           'lan-num_sta', 'wlan-num_sta', 'time', 'rx_bytes', 'tx_bytes']

    dpi_app_categories = {
        0:	"Instant messaging",
        1:	"P2P",
        3:	"File Transfer",
        4:	"Streaming Media",
        5:	"Mail and Collaboration",
        6:	"Voice over IP",
        7:	"Database",
        8:	"Games",
        9:	"Network Management",
        10:	"Remote Access Terminals",
        11:	"Bypass Proxies and Tunnels",
        12:	"Stock Market",
        13:	"Web",
        14:	"Security Update",
        15:	"Web IM",
        17:	"Business",

        18:	"Network Protocols",
        19:	"Network Protocols",
        20:	"Network Protocols",
        23:	"Private Protocol",
        24:	"Social Network",
        255: "Unknown"
    }


    def __init__(self,
                 controller_url,
                 authentication_username,
                 authentication_password,
                 api_client_logger=logging.getLogger()):

        self._logger = api_client_logger
        self._controller_url = controller_url
        self._controller_requests_session = requests.Session()

        # Login to the controller
        url_login = unifi_controller_url + "/api/login"
        self._logger .debug(f"{self} logging in to controller")
        credentials = {"username": authentication_username, "password": authentication_password}
        login_response = self._controller_requests_session.post(url_login,
                                                       headers={"content-type": "application/json"},
                                                       data=json.dumps(credentials),
                                                       verify=False)

        if login_response.status_code != 200:
            err_msg = f"{self} Login failed. HTTP request to {url_login} returned status code {login_response.status_code}. Expected 200."
            self._logger.error(err_msg)
            raise UnifiAPIClientException(err_msg)

        self._logger .debug(f"{self} logged in to controller OK")

    def get_sites(self):

        url_sites = unifi_controller_url + "/api/self/sites"
        self._logger.debug(f"Getting sites from {url_sites}")
        sites_response = self._controller_requests_session.get(url_sites,
                                                      headers={"content-type": "application/json"},
                                                      verify=False)
        if sites_response.status_code != 200:
            err_msg = f"{self} request to sites endpoint {url_sites} returned status code {sites_response.status_code}. Expected 200"
            self._logger.error(err_msg)
            raise UnifiAPIClientException(err_msg)

        self._logger.debug(f"Got sites from {url_sites} OK")

        # TODO Write sites response JSON schema
        # TODO Check sites response against JSON schema
        return sites_response.json()


    def get_devices_for_site(self, site):

        url_devices = unifi_controller_url+"/api/s/"+site+"/stat/device"
        self._logger.debug(f"Getting devices for site {site} from {url_devices}")
        site_devices_response = self._controller_requests_session.get(url_devices,
                                                               headers={"content-type": "application/json"},
                                                               verify=False)
        if site_devices_response.status_code != 200:
            err_msg = f"{self} request to site devicess endpoint {url_devices} returned status code {site_devices_response.status_code}. Expected 200"
            self._logger.error(err_msg)
            raise UnifiAPIClientException(err_msg)

        self._logger.debug(f"Got site devices from {url_devices} OK")

        # TODO Write sites response JSON schema
        # TODO Check sites response against JSON schema
        return site_devices_response.json()

    def get_devices_for_default_site(self):
        return self.get_devices_for_site("default")

    def get_stats_for_site(self, site, interval, element_type,
                           stat_attributes,
                           start_epoch_timestamp_ms=None, end_epoch_timestamp_ms=None,
                           filter_mac_list=None):

        supported_intervals = ['5minutes', 'hourly', 'daily']
        supported_element_types = ['site', 'user', 'ap']

        if interval not in supported_intervals:
            raise ValueError(f"{self} invalid interval value {interval}. Must be one of {supported_intervals}")
        if element_type not in supported_element_types:
            raise ValueError(f"{self} invalid element type value {element_type}. Must be one of {supported_element_types}")
        for stat_attribute in stat_attributes:
            if stat_attribute not in self.all_stat_attributes:
                raise ValueError(f"{self} unsupported stat attribute type value {stat_attribute}. Must be among types {self.all_stat_attributes}")

        url_stat = unifi_controller_url + "/api/s/"+site+"/stat/report/"+interval+"."+element_type
        self._logger.debug(f"{self} getting stats for site {site} for interval {interval} of element type {element_type} from {url_stat}")

        stat_request_parameters = {
            'attrs': stat_attributes
        }
        if start_epoch_timestamp_ms is not None:
            stat_request_parameters['start'] = start_epoch_timestamp_ms
        if end_epoch_timestamp_ms is not None:
            stat_request_parameters['end'] = end_epoch_timestamp_ms
        if filter_mac_list is not None and len(filter_mac_list) > 0:
            stat_request_parameters["macs"] = filter_mac_list

        print(stat_request_parameters)

        stat_device_response = self._controller_requests_session.post(url_stat,
                                                                      headers={"content-type": "application/json"},
                                                                      data=json.dumps(stat_request_parameters),
                                                                      verify=False)

        if stat_device_response.status_code != 200:
            err_msg = f"{self} request to site stat endpoint {url_stat} returned status code {stat_device_response.status_code}. Expected 200"
            self._logger.error(err_msg)
            raise UnifiAPIClientException(err_msg)

        # TODO write site stats json schema
        # TODO check stat_device_response json against site stats json schema
        return stat_device_response.json()

    def get_5min_site_all_stats(self, site, start_epoch_timestamp_ms=None, end_epoch_timestamp_ms=None):
        return self.get_stats_for_site(site, "5minutes", "site",
                                       self.all_stat_attributes,
                                       start_epoch_timestamp_ms, end_epoch_timestamp_ms)

    def get_5min_ap_all_stats(self, site, start_epoch_timestamp_ms=None, end_epoch_timestamp_ms=None):
        return self.get_stats_for_site(site, "5minutes", "ap",
                                       self.all_stat_attributes,
                                       start_epoch_timestamp_ms, end_epoch_timestamp_ms)

    def get_5min_user_all_stats(self, site, start_epoch_timestamp_ms=None, end_epoch_timestamp_ms=None):
        return self.get_stats_for_site(site, "5minutes", "user",
                                       self.all_stat_attributes,
                                       start_epoch_timestamp_ms, end_epoch_timestamp_ms)

    def get_hourly_site_all_stats(self, site, start_epoch_timestamp_ms=None, end_epoch_timestamp_ms=None):
        return self.get_stats_for_site(site, "hourly", "site",
                                       self.all_stat_attributes,
                                       start_epoch_timestamp_ms, end_epoch_timestamp_ms)

    def get_hourly_ap_all_stats(self, site, start_epoch_timestamp_ms=None, end_epoch_timestamp_ms=None):
        return self.get_stats_for_site(site, "hourly", "ap",
                                       self.all_stat_attributes,
                                       start_epoch_timestamp_ms, end_epoch_timestamp_ms)

    def get_hourly_user_all_stats(self, site, start_epoch_timestamp_ms=None, end_epoch_timestamp_ms=None):
        return self.get_stats_for_site(site, "hourly", "user",
                                       self.all_stat_attributes,
                                       start_epoch_timestamp_ms, end_epoch_timestamp_ms)

    def get_monthly_site_all_stats(self, site, start_epoch_timestamp_ms=None, end_epoch_timestamp_ms=None):
        return self.get_stats_for_site(site, "monthly", "site",
                                       self.all_stat_attributes,
                                       start_epoch_timestamp_ms, end_epoch_timestamp_ms)

    def get_monthly_ap_all_stats(self, site, start_epoch_timestamp_ms=None, end_epoch_timestamp_ms=None):
        return self.get_stats_for_site(site, "monthly", "ap",
                                       self.all_stat_attributes,
                                       start_epoch_timestamp_ms, end_epoch_timestamp_ms)

    def get_monthly_user_all_stats(self, site, start_epoch_timestamp_ms=None, end_epoch_timestamp_ms=None):
        return self.get_stats_for_site(site, "monthly", "user",
                                       self.all_stat_attributes,
                                       start_epoch_timestamp_ms, end_epoch_timestamp_ms)

    def get_active_clients(self, site):

        url_active_clients = unifi_controller_url + "/api/s/"+site+"/stat/sta"
        self._logger.debug(f"Getting active clients for site {site} from {url_active_clients}")
        site_active_clients_response = self._controller_requests_session.get(url_active_clients,
                                                               headers={"content-type": "application/json"},
                                                               verify=False)
        if site_active_clients_response.status_code != 200:
            err_msg = f"{self} request to site active clients endpoint {url_active_clients} returned status code {site_active_clients_response.status_code}. Expected 200"
            self._logger.error(err_msg)
            raise UnifiAPIClientException(err_msg)

        self._logger.debug(f"Got site active clients from {url_active_clients} OK")

        # TODO Write sites active clients response JSON schema
        # TODO Check sites active clients response against JSON schema
        return site_active_clients_response.json()


    def get_known_clients(self, site):

        url_known_clients = unifi_controller_url + "/api/s/"+site+"/rest/user"
        self._logger.debug(f"Getting known clients for site {site} from {url_known_clients}")
        site_known_clients_response = self._controller_requests_session.get(url_known_clients,
                                                               headers={"content-type": "application/json"},
                                                               verify=False)
        if site_known_clients_response.status_code != 200:
            err_msg = f"{self} request to site known clients endpoint {url_known_clients} returned status code {site_known_clients_response.status_code}. Expected 200"
            self._logger.error(err_msg)
            raise UnifiAPIClientException(err_msg)

        self._logger.debug(f"Got site known clients from {url_known_clients} OK")

        # TODO Write sites known clients response JSON schema
        # TODO Check sites known clients response against JSON schema
        return site_known_clients_response.json()

    def DOES_NOT_WORK_get_spectrum_scan(self, site, filter_mac_list=None):

        # TODO spectrum scan does not work - returns 404
        url_spectrum_scan = unifi_controller_url + "/api/s/"+site+"/stat/spectrumscan"
        self._logger.debug(f"Getting spectrum for site {site} from {url_spectrum_scan}")
        site_spectrum_scan_response = self._controller_requests_session.get(url_spectrum_scan,
                                                               headers={"content-type": "application/json"},
                                                               verify=False)
        if site_spectrum_scan_response.status_code != 200:
            err_msg = f"{self} request to site spectrum scan endpoint {url_spectrum_scan} returned status code {site_spectrum_scan_response.status_code}. Expected 200"
            self._logger.error(err_msg)
            raise UnifiAPIClientException(err_msg)

        self._logger.debug(f"Got site known clients from {url_spectrum_scan} OK")

        # TODO Write sites known clients response JSON schema
        # TODO Check sites known clients response against JSON schema
        return site_spectrum_scan_response.json()

    def get_ddns_information(self, site):

        url_ddns_info = unifi_controller_url + "/api/s/"+site+"/stat/dynamicdns"
        self._logger.debug(f"Getting dynamic dns info for site {site} from {url_ddns_info}")
        site_ddns_response = self._controller_requests_session.get(url_ddns_info,
                                                                   headers={"content-type": "application/json"},
                                                                   verify=False)
        if site_ddns_response.status_code != 200:
            err_msg = f"{self} request to site ddns info endpoint {url_ddns_info} returned status code {site_ddns_response.status_code}. Expected 200"
            self._logger.error(err_msg)
            raise UnifiAPIClientException(err_msg)

        self._logger.debug(f"Got site ddns info from {site_ddns_response} OK")

        # TODO Write sites known clients response JSON schema
        # TODO Check sites known clients response against JSON schema
        return site_ddns_response.json()


    def get_site_dpi_by_app(self, site, filter_category_list=None):

        url_site_dpi =  unifi_controller_url + "/api/s/"+site+"/stat/sitedpi"

        self._logger.debug(f"Getting site dpi by app for site {site} from {url_site_dpi}")

        parameters = {"type": "by_app"}
        if filter_category_list is not None and len(filter_category_list) > 0:
            parameters["cats"] = filter_category_list

        site_site_dpi_app_response = self._controller_requests_session.post(url_site_dpi,
                                                                        headers={"content-type": "application/json"},
                                                                        data=json.dumps(parameters),
                                                                        verify=False)
        if site_site_dpi_app_response.status_code != 200:
            err_msg = f"{self} request to site dpi by app info endpoint {url_site_dpi} returned status code {site_site_dpi_app_response.status_code}. Expected 200"
            self._logger.error(err_msg)
            raise UnifiAPIClientException(err_msg)

        self._logger.debug(f"Got site dpi by app from {url_site_dpi} OK")

        # TODO Write sites known clients response JSON schema
        # TODO Check sites known clients response against JSON schema
        return site_site_dpi_app_response.json()


    def get_site_dpi_by_category(self, site):

        url_site_dpi =  unifi_controller_url + "/api/s/"+site+"/stat/sitedpi"

        self._logger.debug(f"Getting site dpi by cat for site {site} from {url_site_dpi}")

        parameters = {"type": "by_cat"}

        site_site_dpi_cat_response = self._controller_requests_session.post(url_site_dpi,
                                                                        headers={"content-type": "application/json"},
                                                                        data=json.dumps(parameters),
                                                                        verify=False)
        if site_site_dpi_cat_response.status_code != 200:
            err_msg = f"{self} request to site dpi by category info endpoint {url_site_dpi} returned status code {site_site_dpi_cat_response.status_code}. Expected 200"
            self._logger.error(err_msg)
            raise UnifiAPIClientException(err_msg)

        self._logger.debug(f"Got site ddns info from {url_site_dpi} OK")

        # TODO Write sites dpi by cat response JSON schema
        # TODO Check sites dpi by cat response against JSON schema
        return site_site_dpi_cat_response.json()

    def get_dpi_by_app(self, site, filter_mac_list=None, filter_category_list=None):

        url_dpi = unifi_controller_url + "/api/s/" + site + "/stat/stadpi"

        self._logger.debug(f"Getting dpi by app for site {site} from {url_dpi}")

        parameters = {"type": "by_app"}
        if filter_mac_list is not None and len(filter_mac_list) > 0:
            parameters["macs"] = filter_mac_list
        if filter_category_list is not None and len(filter_category_list) > 0:
            parameters["cats"] = filter_category_list
            # TODO look at dpi by app category filter, doesn't seem to work. all cats are returned

        site_dpi_app_response = self._controller_requests_session.post(url_dpi,
                                                                        headers={"content-type": "application/json"},
                                                                        data=json.dumps(parameters),
                                                                        verify=False)
        if site_dpi_app_response.status_code != 200:
            err_msg = f"{self} request to site dpi by app info endpoint {url_dpi} returned status code {site_dpi_app_response.status_code}. Expected 200"
            self._logger.error(err_msg)
            raise UnifiAPIClientException(err_msg)

        self._logger.debug(f"Got site dpi by app from {url_dpi} OK")

        # TODO Write sites known clients response JSON schema
        # TODO Check sites known clients response against JSON schema
        return site_dpi_app_response.json()

    def get_dpi_by_category(self, site, filter_mac_list=None):

        url_dpi = unifi_controller_url + "/api/s/" + site + "/stat/stadpi"

        self._logger.debug(f"Getting dpi by cat for site {site} from {url_dpi}")

        parameters = {"type": "by_cat"}
        if filter_mac_list is not None and len(filter_mac_list) > 0:
            parameters["macs"] = filter_mac_list

        site_dpi_cat_response = self._controller_requests_session.post(url_dpi,
                                                                        headers={"content-type": "application/json"},
                                                                        data=json.dumps(parameters),
                                                                        verify=False)
        if site_dpi_cat_response.status_code != 200:
            err_msg = f"{self} request to site dpi by category info endpoint {url_dpi} returned status code {site_dpi_cat_response.status_code}. Expected 200"
            self._logger.error(err_msg)
            raise UnifiAPIClientException(err_msg)

        self._logger.debug(f"Got site ddns info from {url_dpi} OK")

        # TODO Write sites known clients response JSON schema
        # TODO Check sites known clients response against JSON schema
        return site_dpi_cat_response.json()



    def __str__(self):
        return f"UnifiAPIClient to {self._controller_url}"

    @staticmethod
    def uri_to_parts(unifi_uri):
        split_unifi_uri = urllib.parse.urlsplit(unifi_uri)

        controller_url = split_unifi_uri.scheme + "://" + str(split_unifi_uri.hostname) + ("" if split_unifi_uri.port is None else ":" + str(split_unifi_uri.port))
        username = split_unifi_uri.username
        password = urllib.parse.unquote(str(split_unifi_uri.password))

        return  controller_url, username, password

    @staticmethod
    def thirty_min_ago():
        return int(arrow.utcnow().shift(minutes=-30).timestamp())*1000, int(arrow.utcnow().timestamp())*1000

    @staticmethod
    def one_hour_ago():
        return int(arrow.utcnow().shift(hours=-1).timestamp())*1000, int(arrow.utcnow().timestamp())*1000

    def get_category_and_application_map(self, angular_build="g9491db021"):

        dynamic_dpi_js = unifi_controller_url + "/manage/angular/" + angular_build + "/js/dynamic.dpi.js"

        dpi_js_response = requests.get(dynamic_dpi_js, verify=False)
        if dpi_js_response.status_code != 200:
            err_msg = f"{self} request to get dynamic dpi js lib {dynamic_dpi_js} returned status code {dpi_js_response.status_code}. Expected 200"
            self._logger.error(err_msg)
            raise UnifiAPIClientException(err_msg)

        beautified_dpi_js = jsbeautifier.beautify(dpi_js_response.text)

        mg = re.match(".*categories: (.*),.*            applications:(.*)}\n    \}, \{\}\],\n    2\:", beautified_dpi_js, re.DOTALL).groups()

        if len(mg) != 2:
            err_msg = f"{self} could not parse dynamic dpi js lib {dynamic_dpi_js}. Regex expected two match groups got {len(mg)}"
            self._logger.error(err_msg)
            raise UnifiAPIClientException(err_msg)

        network_traffic_category_map = yaml.load(mg[0], Loader=yaml.FullLoader)
        network_traffic_application_map = yaml.load(mg[0], Loader=yaml.FullLoader)

        return network_traffic_category_map, network_traffic_application_map



logger = logging.getLogger("UNIFI_CLIENT")
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

if os.environ.get("UNIFI_URI") is None:
    print("Required environment var UNIFI_URI not set. Bailing")
    sys.exit(-1)

unifi_controller_url, unifi_username, unifi_password = UnifiAPIClient.uri_to_parts(os.environ.get("UNIFI_URI"))

unifi_client = UnifiAPIClient(unifi_controller_url, unifi_username, unifi_password, logger)
#print(json.dumps(unifi_client.get_sites(), indent=4))
#print(json.dumps(unifi_client.get_devices_for_default_site(), indent=4))
#print(json.dumps(unifi_client.get_5min_ap_all_stats("default", *unifi_client.one_hour_ago()), indent=4))

app_stats = unifi_client.get_dpi_by_app("default")

#print(json.dumps(unifi_client.get_site_dpi_by_app("default"), indent=4))

cat_map, app_map = unifi_client.get_category_and_application_map()
for device in app_stats["data"]:
    for stat in device["by_app"]:
      stat["x_cat"] = cat_map[stat["cat"]]["name"]
      stat["x_app"] = app_map.get(stat["app"], {"name": "__unlisted__"})["name"]


print(json.dumps(app_stats, indent=4))