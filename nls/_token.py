"""
_token.py

Copyright 1999-present Alibaba Group Holding Ltd.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""


from aliyunsdkcore.client import AcsClient
from aliyunsdkcore.request import CommonRequest

import json

__all__ = ["getToken"]


def getToken(akid, aksecret, domain="cn-shanghai",
             version="2019-02-28",
             url="nls-meta.cn-shanghai.aliyuncs.com"):
    """
    Help methods to get token from aliyun by giving access id and access secret
    key

    Parameters:
    -----------
    akid: str
        access id from aliyun
    aksecret: str
        access secret key from aliyun
    domain: str:
        default is cn-shanghai
    version: str:
        default is 2019-02-28
    url: str
        full url for getting token, default is
        nls-meta.cn-shanghai.aliyuncs.com
    """
    client = AcsClient(akid, aksecret, domain)
    request = CommonRequest()
    request.set_method('POST')
    request.set_domain(url)
    request.set_version(version)
    request.set_action_name('CreateToken')
    response = client.do_action_with_exception(request)
    response_json = json.loads(response)
    if "Token" in response_json:
        token = response_json["Token"]
        if "Id" in token:
            return token["Id"]
        else:
            print(f"No id in token:{token}")
    else:
        print(f"Token not in response:{response_json}")
