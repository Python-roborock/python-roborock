"""Product catalog and plugin download endpoints on the Base IoT API."""

from roborock.data import ProductResponse, UserData
from roborock.exceptions import RoborockException

from ._base import RoborockApiBase


class ProductsApi(RoborockApiBase):
    """Product schemas and device plugin bundles."""

    async def get_products(self, user_data: UserData) -> ProductResponse:
        """Gets all products and their schemas, good for determining status codes and model numbers."""
        product_request = await self._iot_request()
        product_response = await product_request.request(
            "get",
            "/api/v4/product",
            headers={"Authorization": user_data.token},
        )
        if product_response is None:
            raise RoborockException("home_id_response is None")
        if product_response.get("code") != 200:
            raise RoborockException(f"{product_response.get('msg')} - response code: {product_response.get('code')}")
        result = product_response.get("data")
        if isinstance(result, dict):
            return ProductResponse.from_dict(result)
        raise RoborockException("product result was an unexpected type")

    async def download_code(self, user_data: UserData, product_id: int):
        product_request = await self._iot_request()
        request = {"apilevel": 99999, "productids": [product_id], "type": 2}
        response = await product_request.request(
            "post",
            "/api/v1/appplugin",
            json=request,
            headers={"Authorization": user_data.token, "Content-Type": "application/json"},
        )
        return response["data"][0]["url"]

    async def download_category_code(self, user_data: UserData):
        product_request = await self._iot_request()
        response = await product_request.request(
            "get",
            "api/v1/plugins?apiLevel=99999&type=2",
            headers={
                "Authorization": user_data.token,
            },
        )
        return {r["category"]: r["url"] for r in response["data"]["categoryPluginList"]}
