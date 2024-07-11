"""Utils for making final output columns generated by pythonify nicer
Col naming schema follows
<type>.<nlu_ref_identifier>.<field>
IF there is only 1 component_to_resolve of <type> in the component_list, the <type> will/can be ommitted.

- we remove all _<field> suffixex
- replace all '@' with '_'
"""
import logging
from typing import List

from nlu.universe.feature_node_ids import NLP_NODE_IDS
from sparknlp.annotator import *

import nlu
from nlu.pipe.col_substitution import substitution_map_OS
import logging

from nlu.pipe.extractors.extractor_base_data_classes import SparkOCRExtractorConfig
from nlu.universe.feature_universes import NLP_FEATURES
from nlu.universe.logic_universes import AnnoTypes
from nlu.universe.universes import Licenses

logger = logging.getLogger('nlu')

""" NAMING SCHEMAS after pythonify procedure : 
### NAMING RESULT SCHEMA: 


results         = { configs.output_col_prefix+'_results'  : list(map(unpack_result,row))} if configs.get_result else {}
beginnings      = { configs.output_col_prefix+'_beginnings' : list(map(unpack_begin,row))} if configs.get_begin or configs.get_positions else {}
endings         = { configs.output_col_prefix+'_endings'    : next(map(unpack_end,row))} if configs.get_end or configs.get_positions else {}
embeddings      = { configs.output_col_prefix+'_embeddings' : next(map(unpack_embeddings,row))} if configs.get_embeds else {}


### METADATA NAMING SCHEMA

result = dict(zip(list(map(lambda x : 'meta_'+ configs.output_col_prefix + '_' + x, keys_in_metadata)),meta_values_list))




"""
from sparknlp.base import MultiDocumentAssembler


class ColSubstitutionUtils:
    """Utils for substituting col names in Pythonify to short and meaningful names.
    Uses custom rename methods for either PySpark or Pandas
    """
    cleanable_splits = ['ner_converter', 'spell', 'ner_to_chunk_converter', 'train', 'classify', 'ner', 'med_ner', 'dl',
                        'match', 'clean', 'sentiment', 'embed', 'embed_sentence', 'embed_chunk', 'explain', 'pos',
                        'resolve_chunk', 'resolve', ]

    @staticmethod
    def substitute_col_names(df, anno_2_ex, pipe, stranger_cols=[], get_embeddings=False, drop_debug_cols=True):
        """
        Some truly irrelevant cols might be dropped, regardless of anno Extractor config
        Some truly irrelevant cols might be dropped, regardless of anno Extractor config
        0. Get list of annotator classes that are duplicates. Check inside the NLU Component Embelishment
        1. Get list of cols derived by component_to_resolve
        2. Substitute list of cols in DF with custom logic
        """
        substitution_fn = 'TODO'

        anno2final_cols = {}  # mapping of final col names to annotator class Key=AnnoModel, Value=List of Result cols
        new_cols = {}
        if pipe.has_licensed_components:
            from nlu.pipe.col_substitution import substitution_map_HC
        deducted_component_names = ColSubstitutionUtils.deduct_component_names(pipe)
        for c in pipe.components:
            if c.license == Licenses.ocr:
                from nlu.pipe.col_substitution import substitution_map_OCR
                # TODO better substitution
                old2new_anno_cols = {k: k for k in c.spark_output_column_names}
                anno2final_cols[c.model] = list(old2new_anno_cols.values())
                new_cols.update(old2new_anno_cols)
                new_cols = {**new_cols, **(old2new_anno_cols)}
                if type(c.model) in substitution_map_OCR.OCR_anno2substitution_fn.keys():
                    cols = df.columns.tolist()
                    substitution_fn = substitution_map_OCR.OCR_anno2substitution_fn[type(c.model)]['default']
                    old2new_anno_cols = substitution_fn(c, cols, deducted_component_names[c])
                    anno2final_cols[c.model] = list(old2new_anno_cols.values())
                    new_cols = {**new_cols, **(old2new_anno_cols)}
                    continue
            if 'embedding' in c.type and get_embeddings == False: continue
            cols_to_substitute = ColSubstitutionUtils.get_final_output_cols_of_component(c, df, anno_2_ex)
            if len(cols_to_substitute) == 0:
                # finisher cleaned components cols
                continue
            if type(c.model) in substitution_map_OS.OS_anno2substitution_fn.keys():
                substitution_fn = substitution_map_OS.OS_anno2substitution_fn[type(c.model)]['default']
            else:
                substitution_fn = c.pdf_col_name_substitutor

            if pipe.has_licensed_components and substitution_fn != 'TODO':
                if type(c.model) in substitution_map_HC.HC_anno2substitution_fn.keys():
                    substitution_fn = substitution_map_HC.HC_anno2substitution_fn[type(c.model)]['default']
            if substitution_fn == 'TODO':
                logger.info(f"Could not find substitution function for os_components={c}, leaving col names untouched")
                old2new_anno_cols = dict(zip(cols_to_substitute, cols_to_substitute))
                anno2final_cols[c.model] = list(old2new_anno_cols.values())
                new_cols.update(old2new_anno_cols)
                continue

            # dic, key=old_col, value=new_col. Some cols may be omitted and missing from the dic which are deemed irrelevant. Behaivour can be disabled by setting drop_debug_cols=False
            old2new_anno_cols = substitution_fn(c, cols_to_substitute, deducted_component_names[c])
            anno2final_cols[c.model] = list(old2new_anno_cols.values())
            new_cols = {**new_cols, **(old2new_anno_cols)}

        pipe.anno2final_cols = anno2final_cols
        cols_to_rename = list(new_cols.keys())
        for k in cols_to_rename:
            # some cols might not exist because no annotations generated, so we need to double check it really exists
            if k not in df.columns: del new_cols[k]
        return df.rename(columns=new_cols)[
            list(set(new_cols.values()).union(set(stranger_cols)))] if drop_debug_cols else \
            df.rename(columns=new_cols)

    @staticmethod
    def get_final_output_cols_of_component(c, df, anno_2_ex) -> List[str]:
        # get_final_output_cols_of_component(self.components[1], pretty_df, anno_2_ex_config)
        """Get's a list of all columns that have been derived in the pythonify procedure from the component_to_resolve
        os_components in dataframe df for anno_2_ex configs """
        og_output_col = c.spark_output_column_names[0]

        # may be missing because finisher cleaning
        if og_output_col not in anno_2_ex: return []
        configs = anno_2_ex[og_output_col]

        if c.name == NLP_NODE_IDS.FINISHER:
            result_cols = c.model.getOutputCols()
            result_cols = [c for c in df.columns if any(c.startswith(s) for s in result_cols)]
            return result_cols
        result_cols = []
        if isinstance(configs, SparkOCRExtractorConfig):
            # TODO better OCR-EX handling --> Col Name generator function which we use everywhere for unified col naming !!!!!
            # return ['text']
            for col in df.columns:
                if 'meta_' + configs.output_col_prefix in col:
                    base_meta_prefix = 'meta_' + configs.output_col_prefix
                    meta_col_name = base_meta_prefix + col.split(base_meta_prefix)[-1]
                    if meta_col_name in df.columns:
                        # special case for overlapping names with _
                        if col.split(base_meta_prefix)[-1].split('_')[1].isnumeric() and not \
                                c.spark_output_column_names[0].split('_')[-1].isnumeric(): continue
                        if col.split(base_meta_prefix)[-1].split('_')[1].isnumeric() and \
                                c.spark_output_column_names[0].split('_')[-1].isnumeric():
                            id1 = int(col.split(base_meta_prefix)[-1].split('_')[1])
                            id2 = int(c.spark_output_column_names.split('_')[-1])
                            if id1 != id2: continue
                        result_cols.append(meta_col_name)
                    elif c.type == AnnoTypes.CHUNK_CLASSIFIER:
                        result_cols.append(col)
                    else:
                        logger.info(f"Could not find meta col for os_components={c}, col={col}. Ommiting col..")
            return result_cols
        if isinstance(c.model, MultiDocumentAssembler):
            return [f'{NLP_FEATURES.DOCUMENT_QUESTION}_results', f'{NLP_FEATURES.DOCUMENT_QUESTION_CONTEXT}_results']

        if configs.get_annotator_type: result_cols.append(configs.output_col_prefix + '_types')
        if configs.get_result: result_cols.append(configs.output_col_prefix + '_results')
        if configs.get_begin or configs.get_positions: result_cols.append(configs.output_col_prefix + '_beginnings')
        if configs.get_end or configs.get_positions: result_cols.append(configs.output_col_prefix + '_endings')
        if configs.get_embeds: result_cols.append(configs.output_col_prefix + '_embeddings')
        if configs.get_origin: result_cols.append(configs.output_col_prefix + '_origin')
        # find all metadata fields generated by component_to_resolve
        for col in df.columns:
            if 'meta_' + configs.output_col_prefix in col:
                base_meta_prefix = 'meta_' + configs.output_col_prefix
                meta_col_name = base_meta_prefix + col.split(base_meta_prefix)[-1]
                if meta_col_name in df.columns:
                    # special case for overlapping names with _
                    if col.split(base_meta_prefix)[-1].split('_')[1].isnumeric() and not \
                            c.spark_output_column_names[0].split('_')[-1].isnumeric(): continue
                    if col.split(base_meta_prefix)[-1].split('_')[1].isnumeric() and \
                            c.spark_output_column_names[0].split('_')[-1].isnumeric():
                        id1 = int(col.split(base_meta_prefix)[-1].split('_')[1])
                        id2 = int(c.spark_output_column_names.split('_')[-1])
                        if id1 != id2: continue
                    result_cols.append(meta_col_name)
                elif c.type == AnnoTypes.CHUNK_CLASSIFIER:
                    result_cols.append(col)
                else:
                    logger.info(f"Could not find meta col for os_components={c}, col={col}. Ommiting col..")
        return result_cols

    @staticmethod
    def deduct_component_names(pipe):
        """Deduct a meaningful name for Embeddings, classifiers, resolvesr, relation extractors, etc..
        Will return a dict that maps every Annotator Class to a String Name. If String_Name =='' that means, it can be omtited for naming and the
        unique_default name schema should be used,
        since that annotator is unique in the component_list
        """
        # Todo extract name deductable as NLU component attribute
        import nlu.pipe.col_substitution.name_deduction.name_deductable_annotators_OS as deductable_OS
        max_depth = 10
        result_names = {}
        for c in pipe.components:
            is_partially_ready = c.type == AnnoTypes.PARTIALLY_READY
            if is_partially_ready or c.loaded_from_pretrained_pipe:
                if hasattr(c.model, 'getOutputCol'):
                    result_names[c] = c.model.getOutputCol()
                elif hasattr(c.model, 'getOutputCols'):
                    result_names[c] = c.model.getOutputCols()[0]
                else:
                    result_names[c] = str(c.model)
                continue

            result_names[c] = 'UNIQUE'  # assuemd uniqe, if not updated in followign steps
            is_always_name_deductable_component = False
            hc_deducted = False
            if pipe.has_licensed_components:
                import nlu.pipe.col_substitution.name_deduction.name_deductable_annotators_HC as deductable_HC
                if type(c.model) not in deductable_HC.name_deductable_HC and type(
                        c.model) not in deductable_OS.name_deductable_OS:
                    continue
                else:
                    hc_deducted = True
                if type(c.model) in deductable_HC.always_name_deductable_HC: is_always_name_deductable_component = True

            if type(c.model) not in deductable_OS.name_deductable_OS and not hc_deducted and not is_partially_ready:
                continue
            if type(c.model) in deductable_OS.always_name_deductable_OS:
                is_always_name_deductable_component = True

            same_components = []
            for other_c in pipe.components:
                if c is other_c: continue
                if c.type == other_c.type: same_components.append(other_c)
            if len(same_components) or is_always_name_deductable_component:
                # make sure each name is unique among the components of same type
                # if is_partially_ready and c.loaded_from_pretrained_pipe:
                cur_depth = 1
                other_names = [ColSubstitutionUtils.deduct_name_from_nlu_ref_at_depth(other_c) for other_c in
                               same_components]
                c_name = ColSubstitutionUtils.deduct_name_from_nlu_ref_at_depth(c)
                while c_name in other_names and cur_depth < max_depth:
                    cur_depth += 1
                    other_names = [ColSubstitutionUtils.deduct_name_from_nlu_ref_at_depth(other_c) for other_c in
                                   same_components]
                    c_name = ColSubstitutionUtils.deduct_name_from_nlu_ref_at_depth(c, cur_depth)
                result_names[c] = c_name
            else:
                result_names[c] = 'UNIQUE'  # no name insertion required
        return result_names

    @staticmethod
    def deduct_name_from_nlu_ref_at_depth(c, depth=1):
        if isinstance(c.model, MarianTransformer): return c.nlu_ref.split('xx.')[-1].replace('marian.', '')
        splits = c.nlu_ref.split('.')
        # remove all name irrelevant splits
        while len(splits) > 1 and (splits[0] in nlu.Spellbook.pretrained_models_references.keys() or splits[
            0] in ColSubstitutionUtils.cleanable_splits): splits.pop(0)
        if len(splits) == 0:
            if isinstance(c.model, (NerDLModel, NerConverter)): return 'ner'
            return c.nlu_ref.replace("@", "_")
        elif splits[0] == 'sentiment' and len(splits) == 1:
            return 'UNIQUE'
        else:
            return '_'.join(splits[:depth])
