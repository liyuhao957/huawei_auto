StarDots 通过读取客户端发起的 http 请求中的 headers 字段，对相关字段进行验证来完成鉴权，因此所有的开放 API 请求都应该携带这些鉴权字段信息，并且需要注意这些字段区分大小写，所有字段都应该小写。
名称	描述
x-stardots-timestamp	当前时间戳（秒）。与 StarDots 服务器的差异不能超过 60 秒。注意：StarDots 的时区为 Asia/Singapore，即 UTC+8。
x-stardots-nonce	4~20个字符的随机字符串，只能包含大写字母、小写字母和数字，注意此值在60秒内必须是唯一的。
x-stardots-key	StarDots发布的key信息。
x-stardots-sign	签名字段是将以上字段按照一定的签名算法组合生成的字符串，具体的签名算法接下来会介绍。
签名算法
我们假设以下字段值:
key	2dcded8e-f231-4d0a-8498-d10ef0639eb3
secret	Ey1JNRCiJOzaIOIilcyJvteTn5YXykFXUwmiHLymK8LHkITfGPo5mTUdLlg0jPHST9fMwMZKxIKUBvSsT5uxrq0lXuerll3eRW2tbMOsvySRY539L8cR6iRFV2DQqdlzbseyq7k9N0U5pZgj6f43e3MngbIttgSDl1G44IBOwqsI2HVXE5H6mf1bHlvWw6Ziuk8Xcw18AioG47SFBLIatrq6E9yEBJgFgcYysCH8JvY659hhqI3Ii1CA5zVtyNp
x-stardots-timestamp	1728958751
x-stardots-nonce	fQvDmMLnKE
x-stardots-key	2dcded8e-f231-4d0a-8498-d10ef0639eb3
Key和Secret由StarDots颁发，您可以在控制台设置页面找到。
然后我们组装上述字段值:
needSignStr=x-stardots-timestamp + | + secret + | + x-stardots-nonce
接下来，我们计算上面组装的字符串的 MD5 摘要:
signStrAfterMD5=md5("1728958751|Ey1JNRCiJOzaIOIilcyJvteTn5YXykFXUwmiHLymK8LHkITfGPo5mTUdLlg0jPHST9fMwMZKxIKUBvSsT5uxrq0lXuerll3eRW2tbMOsvySRY539L8cR6iRFV2DQqdlzbseyq7k9N0U5pZgj6f43e3MngbIttgSDl1G44IBOwqsI2HVXE5H6mf1bHlvWw6Ziuk8Xcw18AioG47SFBLIatrq6E9yEBJgFgcYysCH8JvY659hhqI3Ii1CA5zVtyNp|fQvDmMLnKE")
  signStrAfterMD5="51dabfe4b47e73d4a3b85fe29c4f1e82"
最后我们将摘要字符串转换为大写:
sign=signStrAfterMD5.toUpperCase()
  sign="51DABFE4B47E73D4A3B85FE29C4F1E82"
因此，x-stardots-sign 字段的最终值为: 51DABFE4B47E73D4A3B85FE29C4F1E82
通用的HTTP响应主体
所有接口响应都保持统一的数据结构:
名称	数据类型	是否必须	描述
code	number	是	服务响应代码。200 表示成功。
message	string	是	操作结果的消息提示。
requestId	string	是	请求的唯一编号，可用于故障排除。
success	boolean	是	业务操作是否成功。
ts	number	是	服务器毫秒时间戳。
data	any	是	业务数据字段，该字段可以为任意数据类型，具体数据类型请参考对应接口。
功能接口
注意所有接口都会有请求速率限制，所有接口共用一套速率限制规则。目前，StarDots 的速率限制为每分钟 300 次。
请求端点:
https://api.stardots.io
空间列表
获取空间列表数据。

请求路径:

/openapi/space/list
请求方法:

GET
请求的内容类型:

application/json
请求参数:

名称	数据类型	是否必须	描述
page	number	否	页码，默认值为1。
pageSize	number	否	每页显示条数，范围为1至100，默认值为20。
请求示例:

/openapi/space/list?page=1&pageSize=50
响应字段:

名称	数据类型	是否必须	描述
name	string	是	空间名称
public	boolean	是	空间的可访问性是否为公开。
createdAt	number	是	空间创建时的系统时间戳（以秒为单位）。时区为 UTC+8。
fileCount	number	是	空间内的文件数量。
响应内容类型:

application/json
响应示例:

{
    "code": 200,
    "data": [
        {
            "createdAt": 1723789637,
            "fileCount": 2,
            "name": "star",
            "public": true
        }
    ],
    "message": "SUCCESS",
    "requestId": "5686efa5-c747-4f63-8657-e6052f8181a9",
    "success": true,
    "ts": 1670899688591
}
创建空间
创建新的空间。

请求路径:

/openapi/space/create
请求方法:

PUT
请求内容类型:

application/json
请求参数:

名称	数据类型	是否必须	描述
space	string	是	空间名称，只能为字母或数字组合，长度为4~15个字符。
public	boolean	否	指定空间是否可公开访问。默认值为false。
请求示例:

{
    "public": false,
    "space": "stardots"
}
响应字段:

名称	数据类型	是否必须	描述
No data
响应内容类型:

application/json
响应示例:

{
    "code": 200,
    "data": null,
    "message": "SUCCESS",
    "requestId": "5686efa5-c747-4f63-8657-e6052f8181a9",
    "success": true,
    "ts": 1670899688591
}
删除空间
删除一个已有的空间，注意必须保证该空间中没有文件，否则删除会失败。

请求路径:

/openapi/space/delete
请求方法:

DELETE
请求内容类型:

application/json
请求参数:

名称	数据类型	是否必须	描述
space	string	是	空间名称，只能为字母或数字组合，长度为4~15个字符。
请求示例:

{
    "space": "stardots"
}
响应字段:

名称	数据类型	是否必须	描述
No data
响应内容类型:

application/json
响应示例:

{
    "code": 200,
    "data": null,
    "message": "SUCCESS",
    "requestId": "5686efa5-c747-4f63-8657-e6052f8181a9",
    "success": true,
    "ts": 1670899688591
}
空间可访问性
切换空间的可访问性。

请求路径:

/openapi/space/accessibility/toggle
请求方法:

POST
请求内容类型:

application/json
请求参数:

名称	数据类型	是否必须	描述
space	string	是	空间名称，只能为字母或数字组合，长度为4~15个字符。
public	boolean	否	指定空间是否可公开访问。默认值为false。
请求示例:

{
    "public": false,
    "space": "stardots"
}
响应字段:

名称	数据类型	是否必须	描述
No data
响应内容类型:

application/json
响应示例:

{
    "code": 200,
    "data": null,
    "message": "SUCCESS",
    "requestId": "5686efa5-c747-4f63-8657-e6052f8181a9",
    "success": true,
    "ts": 1670899688591
}
空间内的文件列表
获取空间内文件列表，列表按照文件上传时间降序排列。

请求路径:

/openapi/file/list
请求方法:

GET
请求内容类型:

application/json
请求参数:

名称	数据类型	是否必须	描述
space	string	是	空间名称，只能为字母或数字组合，长度为4~15个字符。
page	number	否	页码，默认值为1。
pageSize	number	否	每页显示条数范围为1至100，默认值为20。
请求示例:

{
    "space": "stardots",
    "page": 1,
    "pageSize": 20
}
响应字段:

名称	数据类型	是否必须	描述
page	number	是	页码，默认值为1。
pageSize	number	是	每页显示条数范围为1至100，默认值为20。
totalCount	number	是	总的文件数量。
list	array<object>	是	文件列表数组。
list.name	string	是	文件名称
list.byteSize	number	是	文件的字节大小。
list.size	string	是	文件大小，已格式化以便于阅读。
list.uploadedAt	number	是	文件上传的时间戳（以秒为单位）。时区为 UTC+8。
list.url	string	是	文件的访问地址，注意如果该空间的可访问性为private，则该字段值会携带访问票据，有效期为20秒。
响应内容类型:

application/json
响应示例:

{
    "code": 0,
    "data": {
        "list": [
            {
                "byteSize": 3600000,
                "name": "star",
                "size": "35KB",
                "uploadedAt": 1723789637,
                "url": "https://....."
            }
        ],
        "page": 1,
        "pageSize": 10,
        "totalCount": 1
    },
    "message": "SUCCESS",
    "requestId": "5686efa5-c747-4f63-8657-e6052f8181a9",
    "success": true,
    "ts": 1670899688591
}
文件临时访问票据
获取文件的访问票，当空间的可访问性为私密时，需要携带访问票才能访问该空间下的文件，否则请求将被拒绝。

请求路径:

/openapi/file/ticket
请求方法:

POST
请求内容类型:

application/json
请求参数:

名称	数据类型	是否必须	描述
space	string	是	空间名称，只能为字母或数字组合，长度为4~15个字符。
filename	string	是	文件的名称，不超过170个字符。
请求示例:

{
    "filename": "1.jpg",
    "space": "stardots"
}
响应内容:

名称	数据类型	是否必须	描述
ticket	string	是	临时访问票据
响应内容类型:

application/json
响应示例:

{
    "code": 200,
    "data": {
    "ticket": "a312.."
    },
    "message": "SUCCESS",
    "requestId": "5686efa5-c747-4f63-8657-e6052f8181a9",
    "success": true,
    "ts": 1670899688591
}
文件上传
将文件上传到空间。注意，此请求需要你以表单的形式发起请求。

请求路径:

/openapi/file/upload
请求方法:

PUT
请求内容类型:

multipart/form-data
请求参数:

名称	数据类型	是否必须	描述
space	string	是	空间名称，只能为字母或数字组合，长度为4~15个字符。
file	binary	是	文件的二进制流。注意，文件名称不得超过170个字符。文件大小不能超过10MB。
请求示例:

响应字段:

名称	数据类型	是否必须	描述
space	string	是	空间名称，只能为字母或数字组合，长度为4~15个字符。
filename	string	是	文件的名称。
url	string	是	文件的访问链接，如果空间的可访问性为私密，则访问链接会携带访问票。
响应内容类型:

application/json
响应示例:

{
    "code": 200,
    "data": {
        "filename": "1.png",
        "space": "space",
        "url": "https://i.stardots.io/space/1.png"
    },
    "message": "SUCCESS",
    "requestId": "5686efa5-c747-4f63-8657-e6052f8181a9",
    "success": true,
    "ts": 1670899688591
}
删除文件
删除空间内的文件。此接口支持批量操作。

请求路径:

/openapi/file/delete
请求方法:

DELETE
请求内容类型:

application/json
请求参数:

名称	数据类型	是否必须	描述
space	string	是	空间名称，只能为字母或数字组合，长度为4~15个字符。
filenameList	array<string>	是	文件名称字符串数组。
请求示例:

{
    "filenameList": ["1.jpg", "2.jpg"],
    "space": "stardots"
}
响应字段:

名称	数据类型	是否必须	描述
No data
响应内容类型:

application/json
响应示例:

{
    "code": 0,
    "data": null,
    "message": "SUCCESS",
    "requestId": "5686efa5-c747-4f63-8657-e6052f8181a9",
    "success": true,
    "ts": 1670899688591
}