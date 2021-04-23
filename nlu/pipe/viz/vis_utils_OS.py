from sparknlp_display import NerVisualizer,DependencyParserVisualizer
from sparknlp.annotator import NerConverter,DependencyParserModel, TypedDependencyParserModel, PerceptronModel
from sparknlp.base import  DocumentAssembler
class VizUtilsOS():
    """Utils for interfacing with the Spark-NLP-Display lib and vizzing Open Source Components"""
    @staticmethod
    def infer_viz_open_source(pipe)->str:
        """For a given NLUPipeline with only open source components, infers which visualizations are applicable. """
        for c in pipe.components:
            if isinstance(c.model, NerConverter) : return 'ner'
            if isinstance(c.model, DependencyParserModel) : return 'dep'
    @staticmethod
    def viz_ner(anno_res, pipe,labels = [] ,  viz_colors={}, ):
        """Infer columns required for ner viz and then viz it.
        viz_colors :  set label colors by specifying hex codes , i.e. viz_colors =  {'LOC':'#800080', 'PER':'#77b5fe'}
        labels : only allow these labels to be displayed. (default: [] - all labels will be displayed)
        """
        document_col,entities_col =  VizUtilsOS.infer_ner_dependencies(pipe)
        ner_vis = NerVisualizer()
        if len(viz_colors) > 0 : ner_vis.set_label_colors(viz_colors)
        ner_vis.display(anno_res,label_col=entities_col,document_col=document_col, labels=labels )







    @staticmethod
    def infer_ner_dependencies(pipe):
        """Finds entities and doc cols for ner viz"""
        doc_component      = None
        entities_component = None
        for c in pipe.components:
            if isinstance(c.model, NerConverter) :        entities_component  = c
            if isinstance(c.model, DocumentAssembler) :   doc_component = c

        document_col     = doc_component.info.outputs[0]
        entities_col = entities_component.info.outputs[0]
        return document_col, entities_col


    @staticmethod
    def viz_dep(anno_res,pipe):
        """Viz dep result"""
        pos_col,dep_typ_col,dep_untyp_col  = VizUtilsOS.infer_dep_dependencies(pipe)
        dependency_vis = DependencyParserVisualizer()
        dependency_vis.display(anno_res,pos_col =pos_col,dependency_col =  dep_untyp_col ,dependency_type_col = dep_typ_col)

    @staticmethod
    def infer_dep_dependencies(pipe):
        """Finds entities,pos,dep_typed,dep_untyped and  doc cols for dep viz viz"""
        # doc_component      = None
        pos_component = None
        dep_untyped_component = None
        dep_typed_component = None
        for c in pipe.components:
            if isinstance(c.model, PerceptronModel) :              pos_component  = c
            if isinstance(c.model, TypedDependencyParserModel) :   dep_typed_component  = c
            if isinstance(c.model, DependencyParserModel) :        dep_untyped_component  = c

        pos_col       = pos_component.info.outputs[0]
        dep_typ_col   = dep_typed_component.info.outputs[0]
        dep_untyp_col = dep_untyped_component.info.outputs[0]
        return pos_col,dep_typ_col,dep_untyp_col





