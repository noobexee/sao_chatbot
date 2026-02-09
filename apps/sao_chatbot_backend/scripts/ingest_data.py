from src.app.utils.preprocess_dataset import run_indexing_pipeline

if __name__ == "__main__":
    regulation_path_file = "metadata/ระเบียบ/"
    guideline_path_file = "metadata/แนวทาง/"
    order_path_file = "metadata/คำสั่ง/"
    #run_indexing_pipeline("metadata/init")

    run_indexing_pipeline(regulation_path_file)
    run_indexing_pipeline(guideline_path_file)
    run_indexing_pipeline(order_path_file)
