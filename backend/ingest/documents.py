import os

def process_dir(folder_path):
    """
    Converts a folder path to a list of absolute paths for files within it
    (non-recursive).
    """
    document_paths = []
    # Iterate over all entries in the directory
    for entry_name in os.listdir(folder_path):
        full_path = os.path.join(folder_path, entry_name)
        # Check if the entry is a file (and not a directory)
        if os.path.isfile(full_path):
            document_paths.append(os.path.abspath(full_path))
    return document_paths