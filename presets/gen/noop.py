import shutil

def generate(task, token, team):
    src_path = task.genfiles.src_path
    gen_path = task.genfiles.get_gen_path(token)
    task.genfiles.prepare(token)
    
    shutil.copytree(src_path, gen_path)
    return task
