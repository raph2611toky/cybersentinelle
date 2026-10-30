"""Contrats OpenAPI des quatre endpoints de session admin (une vue = un verbe)."""
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

string = lambda: openapi.Schema(type=openapi.TYPE_STRING)
err = openapi.Schema(type=openapi.TYPE_OBJECT,properties={
    'error':openapi.Schema(type=openapi.TYPE_OBJECT,properties={
       'code':string(),'message':string()})})
user = openapi.Schema(type=openapi.TYPE_OBJECT,properties={
    'id':string(),'username':string(),'name':string(),'email':string(),
    'is_staff':openapi.Schema(type=openapi.TYPE_BOOLEAN),
    'role':string(),
    'permissions':openapi.Schema(type=openapi.TYPE_ARRAY,items=string()),
})
profile=openapi.Schema(type=openapi.TYPE_OBJECT,properties={'user':user})
login_body=openapi.Schema(type=openapi.TYPE_OBJECT,required=['username','password'],properties={
    'username':string(),'password':openapi.Schema(type=openapi.TYPE_STRING,format='password'),
})
csrf_doc=swagger_auto_schema(
    operation_description='Prépare csrftoken. Cookie nécessaire avant un POST de connexion.',
    tags=['Admin / session'],responses={200:openapi.Schema(type=openapi.TYPE_OBJECT,properties={'csrf':string()}),500:err},
    security=[])
login_doc=swagger_auto_schema(
    operation_description='Connexion réservée au staff. sessionid HttpOnly + rotation session et CSRF. Aucun JWT exposé en JavaScript.',
    tags=['Admin / session'],request_body=login_body,responses={200:profile,400:err,401:err,403:err,500:err},security=[])
me_doc=swagger_auto_schema(
    operation_description='État de la session staff active (permissions Django).',
    tags=['Admin / session'],responses={200:profile,403:err,500:err})
logout_doc=swagger_auto_schema(
    operation_description='Invalide la session staff. En-tête X-CSRFToken requis.',
    tags=['Admin / session'],request_body=openapi.Schema(type=openapi.TYPE_OBJECT),
    responses={200:openapi.Schema(type=openapi.TYPE_OBJECT,properties={'logged_out':openapi.Schema(type=openapi.TYPE_BOOLEAN)}),403:err,500:err})
