# Python
from os.path import isfile
# Spark
from pyspark.sql.dataframe import DataFrame
from pyspark.sql.types import *
# Forklift
# N&S
from .column_renamer import ColumnRenamer
from .column_deleter import ColumnDeleter
from .cell_caster import CellCaster
from .cell_caster import CastProcessor
from .stages import *
# Move
from .warehouse import Warehouse

class Forklift(object):
  def __init__(self, sql_context):
    self.sql_context = sql_context

  @classmethod
  def validate_list_of_stages(klass, stages):
    if not isinstance(stages, list):
      return False
    return not (False in [True if ForkliftNSStage in stage.__bases__ else False for stage in stages])

  def normalize_and_sanitize(self, dataframe, with_spark_schema, remappings_file_path, cast_processor, stages=[NS_ALL]):
    print("Step 1: Check that arguments are valid")
    if not isinstance(dataframe, DataFrame):
      raise TypeError("dataframe must be an instance of Dataframe")
    if len(dataframe.columns) < 1:
      raise ValueError("dataframe must have 1 or more columns")
    if dataframe.count() < 1:
      raise ValueError("dataframe must have 1 or more rows")
    if not isinstance(with_spark_schema, StructType):
      raise TypeError("with_spark_schema must be an instance of StructType")
    if len(with_spark_schema) < 1:
      raise ValueError("with_spark_schema must have at least one StructField column")
    if not isfile(remappings_file_path):
      raise ValueError("remappings_file_path must be a file that exists")
    if not CastProcessor in cast_processor.__bases__:
      raise TypeError("cast_processor must be a child class of CastProcessor")
    if not self.validate_list_of_stages(stages):
      raise TypeError("stages must be a list of ForkliftNSStage")

    if any([stage in stages for stage in [NS_ALL, NS_RENAME_COLS]]):
      print("Step 2: Rename all columns, according to the mapping")
      column_renamer = ColumnRenamer(remappings_file_path)
      dataframe = column_renamer.rename_columns(dataframe)
    else:
      print("Skipping Step 2: Rename all columns, according to the mapping")

    if any([stage in stages for stage in [NS_ALL, NS_DELETE_COLS]]):
      print("Step 3: Delete unwanted columns, according to the mapping")
      column_deleter = ColumnDeleter(remappings_file_path)
      dataframe = column_deleter.delete_columns(dataframe)
    else:
      print("Skipping Step 3: Delete unwanted columns, according to the mapping")

    if any([stage in stages for stage in [NS_ALL, NS_CAST_CELLS]]):
      print("Step 4: Cast each cell, according to the Caster instance provided")
      caster = CellCaster(cast_processor, with_spark_schema, self.sql_context)
      dataframe = caster.cast(dataframe)
    else:
      print("Skipping Step 4: Cast each cell, according to the Caster instance provided")

    print("Step 5: Return the normalized and sanitized dataframe")
    return dataframe

  def move(self, from_options, to_options):
    print("Step 1: Check that arguments are valid")
    if not isinstance(from_options, dict):
      raise TypeError("from_options must be a Dictionary (dict)")
    if not isinstance(to_options, dict):
      raise TypeError("to_options must be a Dictionary (dict)")
    if len(from_options) < 1:
      raise ValueError("from_options can't be empty")
    if len(to_options) < 1:
      raise ValueError("to_options can't be empty")
    
    print("Step 2: Create a warehouse flyweight")
    warehouse = Warehouse()

    print("Step 3: Load the dataframe")
    from_df = warehouse.read(self.sql_context, from_options)

    print("Step 4: Write the dataframe")
    warehouse.write(from_df, to_options)
    
    return