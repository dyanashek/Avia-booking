from django.test import TestCase

# Create your tests here.

# async def create_icount_client(user, phone):
#     cl_name = user.name
#     if user.family_name:
#         cl_name += f' {user.family_name}'
#     data = {
#         'cid': ICOUNT_COMPANY_ID,
#         'user': ICOUNT_USERNAME,
#         'pass': ICOUNT_PASSWORD,
#         'client_name': cl_name,
#         'first_name': user.name,
#         'last_name': user.family_name,
#         'mobile': phone
#     }
#     headers = {
#         'Content-Type': 'application/x-www-form-urlencoded',  # Как form-data
#         'User-Agent': 'Mozilla/5.0'  # Имитируем обычный браузер
#     }
#     async with aiohttp.ClientSession() as session:
#         try:
#             ssl_context = ssl.create_default_context()
#             ssl_context.load_verify_locations(certifi.where())
#             async with session.post(ICOUNT_CREATE_USER_ENDPOINT, data=data, ssl=False) as response:
#                     if response.status == 200:
#                         response_data = await response.json()
#                         icount_client_id = response_data.get('client_id')
#                     else:
#                         icount_client_id = False
#         except Exception:
#             icount_client_id = False

#     return icount_client_id


# async def create_icount_invoice(user_id, amount, is_old_sim=False):
#     icount_cid = ICOUNT_COMPANY_ID
#     icount_user = ICOUNT_USERNAME
#     icount_pass = ICOUNT_PASSWORD
#     if is_old_sim:
#         icount_cid = OLD_ICOUNT_COMPANY_ID
#         icount_user = OLD_ICOUNT_USERNAME
#         icount_pass = OLD_ICOUNT_PASSWORD

#     data = {
#         'cid': icount_cid,
#         'user': icount_user,
#         'pass': icount_pass,
#         'doctype': 'invrec',
#         'client_id': user_id,
#         'lang': 'en',
#         'items': [
#             {
#                 'description': 'Online support + simcard',
#                 'unitprice_incvat': float(amount),
#                 'quantity': 1,
#             },
#             ],
#         'cash': {'sum': float(amount)},        
#     }

#     async with aiohttp.ClientSession() as session:
#         try:
#             ssl_context = ssl.create_default_context()
#             ssl_context.load_verify_locations(certifi.where())
#             async with session.post(ICOUNT_CREATE_INVOICE_ENDPOINT, json=data, ssl=ssl_context) as response:
#                     if response.status == 200:
#                         response_data = await response.json()
#                         doc_url = response_data.get('doc_url')
#                     else:
#                         doc_url = False
#         except Exception as ex:
#             doc_url = False

#     return doc_url