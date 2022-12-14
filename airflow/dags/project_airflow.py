from datetime import datetime, timedelta
import os
from airflow import DAG
from airflow.operators.dummy_operator import DummyOperator
from airflow.operators.postgres_operator import PostgresOperator
from airflow.operators import (StageToRedshiftOperator, LoadFactOperator,
                                LoadDimensionOperator, DataQualityOperator)
from helpers import SqlQueries

#AWS_KEY = os.environ.get('AWS_KEY')
#AWS_SECRET = os.environ.get('AWS_SECRET')

default_args = {
    'owner': 'udacity',
    'start_date': datetime(2019, 1, 12),
    'depends_on_past' : False,
    'retries' : 3,
    'retry_delay' : timedelta(minutes=5),
    'catchup': False,
    'email_on_retry' : False
}

dag = DAG('project_airflow',
          default_args=default_args, #If a dictionary of default_args is passed to a DAG, it will apply them to any of its operators. This makes it easy to apply a common parameter to many operators without having to type it many time
          description='Load and transform data in Redshift with Airflow',
          schedule_interval='0 * * * *' 
          #means run once an hour at the beginning of the hour; https://stackoverflow.com/a/64488244 
        )

start_operator = DummyOperator(task_id='Begin_execution',  dag=dag)

#create_tables_task = PostgresOperator(
#    task_id="create_tables",
#    dag=dag,
#    sql='create_tables.sql',
#    postgres_conn_id="redshift",
#)

stage_events_to_redshift = StageToRedshiftOperator(
    task_id='Stage_events',
    dag=dag,
    table="staging_events",
    redshift_conn_id="redshift",
    aws_credentials_id="aws_credentials",
    s3_bucket="udacity-dend",
    s3_key="log_data",
    json_path="s3://udacity-dend/log_json_path.json", # info on this here: https://knowledge.udacity.com/questions/185421
)

stage_songs_to_redshift = StageToRedshiftOperator(
    task_id='Stage_songs',
    dag=dag,
    redshift_conn_id="redshift",
    aws_credentials_id="aws_credentials",
    table="staging_songs",
    s3_bucket="udacity-dend",
    s3_key="song_data/A/A/A", #change this to song_data for the full dataset, see here: https://knowledge.udacity.com/questions/592845 
    json_path="auto",
)

load_songplays_table = LoadFactOperator(
    task_id='Load_songplays_fact_table',
    dag=dag,
    redshift_conn_id="redshift",
    table="songplays",
    sql_query=SqlQueries.songplay_table_insert,
)

load_user_dimension_table = LoadDimensionOperator(
    task_id='Load_user_dim_table',
    dag=dag,
    redshift_conn_id="redshift",
    table="users",
    sql_query=SqlQueries.user_table_insert,
    append=False,
)

load_song_dimension_table = LoadDimensionOperator(
    task_id='Load_song_dim_table',
    dag=dag,
    redshift_conn_id="redshift",
    table="songs",
    sql_query=SqlQueries.song_table_insert,
    append=False,
)

load_artist_dimension_table = LoadDimensionOperator(
    task_id='Load_artist_dim_table',
    dag=dag,
    redshift_conn_id="redshift",
    table="artists",
    sql_query=SqlQueries.artist_table_insert,
    append=False,
)

load_time_dimension_table = LoadDimensionOperator(
    task_id='Load_time_dim_table',
    dag=dag,
    redshift_conn_id="redshift",
    table="time",
    sql_query=SqlQueries.time_table_insert,
    append=False,
)

run_quality_checks = DataQualityOperator(
    task_id='Run_data_quality_checks',
    dag=dag,
    redshift_conn_id="redshift",
    check_stmts=[
        {
            'sql': 'SELECT COUNT(*) FROM songplays;',
            'operator': 'greater than',
            'value': 0
        },
        {
            'sql': 'SELECT COUNT(*) FROM songplays WHERE songid IS NULL;',
            'operator': 'equal',
            'value': 0
        },
        {
            'sql': 'SELECT COUNT(*) FROM users;',
            'operator': 'greater than',
            'value': 0
        },
                {
            'sql': 'SELECT COUNT(*) FROM users WHERE userid IS NULL;',
            'operator': 'equal',
            'value': 0
        },
        {
            'sql': 'SELECT COUNT(*) FROM songs;',
            'operator': 'greater than',
            'value': 0
        },
        {
            'sql': 'SELECT COUNT(*) FROM songs WHERE songid IS NULL;',
            'operator': 'equal',
            'value': 0
        },
        {
            'sql': 'SELECT COUNT(*) FROM artists;',
            'operator': 'greater than',
            'value': 0
        },
        {
            'sql': 'SELECT COUNT(*) FROM artists WHERE artistid IS NULL;',
            'operator': 'equal',
            'value': 0
        },
        {
            'sql': 'SELECT COUNT(*) FROM time;',
            'operator': 'greater than',
            'value': 0
        },
        {
            'sql': 'SELECT COUNT(*) FROM time WHERE start_time IS NULL;',
            'operator': 'equal',
            'value': 0
        }
    ]
    
)

end_operator = DummyOperator(task_id='Stop_execution',  dag=dag)

#start_operator >> create_tables_task
#create_tables_task >> stage_events_to_redshift
#create_tables_task >> stage_songs_to_redshift
start_operator >> stage_events_to_redshift
start_operator >> stage_events_to_redshift
stage_events_to_redshift >> load_songplays_table
stage_songs_to_redshift >> load_songplays_table
load_songplays_table >> load_user_dimension_table
load_songplays_table >> load_song_dimension_table
load_songplays_table >> load_artist_dimension_table
load_songplays_table >> load_time_dimension_table
load_user_dimension_table >> run_quality_checks
load_song_dimension_table >> run_quality_checks
load_artist_dimension_table >> run_quality_checks
load_time_dimension_table >> run_quality_checks
run_quality_checks >> end_operator
