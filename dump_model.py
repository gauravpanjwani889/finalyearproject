import matlab.engine, os
mp = os.path.abspath(r"matlab\main_model.slx")
print("model:", mp, os.path.exists(mp))
eng = matlab.engine.start_matlab()
eng.cd(os.getcwd(), nargout=0)
eng.load_system(mp, nargout=0)
eng.eval("""
fid = fopen('model_dump.txt','w');
b = find_system('main_model','Type','Block');
for i=1:numel(b)
  fprintf(fid,'## %s | %s\\n', b{i}, get_param(b{i},'BlockType'));
  try
    dp = get_param(b{i},'DialogParameters');
    f = fieldnames(dp);
    for k=1:numel(f)
      try
        v = get_param(b{i}, f{k});
        if isnumeric(v), v = mat2str(v); end
        fprintf(fid,'   %s = %s\\n', f{k}, char(string(v)));
      catch
      end
    end
  catch
  end
end
fclose(fid);
""", nargout=0)
eng.quit()
print("done: model_dump.txt")
