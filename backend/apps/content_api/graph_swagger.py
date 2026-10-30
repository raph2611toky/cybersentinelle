"""OpenAPI du brouillon React Flow et de la synchronisation relationnelle."""
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

simple_graph=openapi.Schema(type=openapi.TYPE_OBJECT,required=['nodes','edges'],properties={
    'nodes':openapi.Schema(type=openapi.TYPE_ARRAY,items=openapi.Schema(type=openapi.TYPE_OBJECT)),
    'edges':openapi.Schema(type=openapi.TYPE_ARRAY,items=openapi.Schema(type=openapi.TYPE_OBJECT)),
})
graph_response=openapi.Schema(type=openapi.TYPE_OBJECT,properties={
    'graph':simple_graph,'revision':openapi.Schema(type=openapi.TYPE_INTEGER),
'draft_id':openapi.Schema(type=openapi.TYPE_STRING, read_only=True),
'translation_state':openapi.Schema(type=openapi.TYPE_OBJECT),
'node_id_map':openapi.Schema(type=openapi.TYPE_OBJECT, description='Correspondance des clés React Flow avec les UUID des nœuds Django déjà appliqués', additional_properties=openapi.Schema(type=openapi.TYPE_STRING, format='uuid'))})
graph_input=openapi.Schema(type=openapi.TYPE_OBJECT,required=['graph','revision'],properties={
    'graph':simple_graph,'revision':openapi.Schema(type=openapi.TYPE_INTEGER,minimum=0)})
error=openapi.Schema(type=openapi.TYPE_OBJECT,properties={
    'error':openapi.Schema(type=openapi.TYPE_OBJECT,properties={
        'code':openapi.Schema(type=openapi.TYPE_STRING),
        'message':openapi.Schema(type=openapi.TYPE_STRING),
        'fields':openapi.Schema(type=openapi.TYPE_OBJECT),
    })})
read_doc=swagger_auto_schema(tags=['Admin / graphes'],operation_description='Lecture d’un brouillon graphique ou reconstruction à partir de Noeud/OptionDecision.',responses={200:graph_response,403:error,404:error})
save_doc=swagger_auto_schema(tags=['Admin / graphes'],operation_description='Sauvegarde versionnée du brouillon React Flow. Cette étape ne publie rien.',request_body=graph_input,responses={200:graph_response,400:error,403:error,409:error})
apply_doc=swagger_auto_schema(tags=['Admin / graphes'],operation_description='Application atomique d’un graphe valide aux Noeud et OptionDecision. Les sorties incomplètes et suppressions de médias liés sont refusées.',request_body=openapi.Schema(type=openapi.TYPE_OBJECT),responses={200:openapi.Schema(type=openapi.TYPE_OBJECT,properties={'applied':openapi.Schema(type=openapi.TYPE_BOOLEAN),'nodes':openapi.Schema(type=openapi.TYPE_INTEGER),'message':openapi.Schema(type=openapi.TYPE_STRING)}),400:error,403:error,409:error})
