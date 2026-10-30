% Deep audit script for main_model.slx
clc;
fprintf('======================================================================\n');
fprintf('SIMULINK MODEL AUDIT & SIGNAL INVESTIGATION\n');
fprintf('======================================================================\n');

model = 'main_model';
load_system(model);

%% 1. MEASUREMENT BLOCK CONNECTIVITY
meas_block = [model '/Three-Phase V-I Measurement'];
fprintf('\n--- 1. MEASUREMENT BLOCK CONNECTIVITY ---\n');
fprintf('Block: %s\n', meas_block);
fprintf('VoltageMeasurement: %s\n', get_param(meas_block, 'VoltageMeasurement'));
fprintf('CurrentMeasurement: %s\n', get_param(meas_block, 'CurrentMeasurement'));

bh = get_param(meas_block, 'Handle');
pc = get_param(bh, 'PortConnectivity');
for i = 1:length(pc)
    src_names = '';
    for j = 1:length(pc(i).SrcBlock)
        if pc(i).SrcBlock(j) > 0
            src_names = [src_names get_param(pc(i).SrcBlock(j), 'Name') ' '];
        end
    end
    dst_names = '';
    for j = 1:length(pc(i).DstBlock)
        if pc(i).DstBlock(j) > 0
            dst_names = [dst_names get_param(pc(i).DstBlock(j), 'Name') ' '];
        end
    end
    fprintf('  Port %d (%s): Src=[%s] Dst=[%s]\n', i, pc(i).Type, strtrim(src_names), strtrim(dst_names));
end

%% 2. PHYSICAL NETWORK TOPOLOGY (TRACE ELECTRICAL PATH)
fprintf('\n--- 2. PHYSICAL NETWORK COMPONENT TRACE ---\n');
blocks = find_system(model, 'Type', 'Block');
fprintf('Total Blocks: %d\n', length(blocks));

%% 3. COMPONENT PARAMETERS
fprintf('\n--- 3. DETAILED COMPONENT PARAMETERS ---\n');
disp_block_params(model, 'Synchronous Machine pu Standard');
disp_block_params(model, 'Three-Phase Transformer (Two Windings)');
disp_block_params(model, 'Three-Phase Series RLC Branch');
disp_block_params(model, 'Series VSC 1');
disp_block_params(model, 'Series VSC 2');
disp_block_params(model, 'Three-Phase Breaker');
disp_block_params(model, 'Three-Phase PI Section Line');
disp_block_params(model, 'Three-Phase Parallel RLC Load');
disp_block_params(model, 'Three-Phase Fault');

%% 4. CHECK MATPOWER
fprintf('\n--- 4. MATPOWER CHECK ---\n');
fprintf('  which runpf: %s\n', which('runpf'));
fprintf('  which case118: %s\n', which('case118'));
fprintf('  which case57: %s\n', which('case57'));

%% 5. EXECUTE 1-SECOND NORMAL SIMULATION & EXPORT RAW DATA
fprintf('\n--- 5. RUNNING 1.0s NORMAL SIMULATION ---\n');
fault_b = [model '/Three-Phase Fault'];
set_param(fault_b, 'FaultA', 'off');
set_param(fault_b, 'FaultB', 'off');
set_param(fault_b, 'FaultC', 'off');
set_param(fault_b, 'GroundFault', 'off');
clear ScopeData simOut scopeObj;

t_start = tic;
simOut = sim(model);
sim_time = toc(t_start);
fprintf('Simulation completed in %.2f seconds.\n', sim_time);

if exist('ScopeData', 'var')
    scopeObj = ScopeData;
elseif exist('simOut', 'var') && isa(simOut, 'Simulink.SimulationOutput')
    scopeObj = simOut.get('ScopeData');
end

t = scopeObj.time;
sig = scopeObj.signals.values;
if size(sig, 1) ~= length(t)
    sig = sig';
end
fprintf('Extracted %d samples across %d channels.\n', size(sig, 1), size(sig, 2));

% Ensure scratch directory exists
if ~exist('scratch', 'dir')
    mkdir('scratch');
end

% Save raw data in MATLAB v7 format (readable by scipy.io.loadmat)
save('scratch/raw_normal_v7.mat', 't', 'sig', '-v7');
fprintf('Saved raw data to scratch/raw_normal_v7.mat\n');

%% 6. ANALYZE VOLTAGE AT STARTUP (0.0s - 0.15s) VS STEADY STATE (0.15s - 1.0s)
fprintf('\n--- 6. VOLTAGE HARMONIC & TRANSIENT ANALYSIS ---\n');
va = sig(:, 1);
vb = sig(:, 2);
vc = sig(:, 3);
ia = sig(:, 4);
ib = sig(:, 5);
ic = sig(:, 6);
trip = sig(:, 7);
vmag = sig(:, 8);
imag = sig(:, 9);

mask_startup = t <= 0.15;
mask_steady = t > 0.15;

fprintf('Startup (0.0 - 0.15s): max Va=%.2f V, min Va=%.2f V, RMS=%.2f V\n', ...
    max(va(mask_startup)), min(va(mask_startup)), sqrt(mean(va(mask_startup).^2)));
fprintf('Steady-State (0.15 - 1.0s): max Va=%.2f V, min Va=%.2f V, RMS=%.2f V\n', ...
    max(va(mask_steady)), min(va(mask_steady)), sqrt(mean(va(mask_steady).^2)));

fprintf('Trip signal range: min=%.2f, max=%.2f\n', min(trip), max(trip));
fprintf('Vmag range: min=%.2f V, max=%.2f V\n', min(vmag), max(vmag));
fprintf('Imag range: min=%.2f A, max=%.2f A\n', min(imag), max(imag));

fprintf('\n======================================================================\n');
fprintf('AUDIT SCRIPT COMPLETE\n');
fprintf('======================================================================\n');

% Local Helper Functions
function disp_block_params(model, block_name)
    bpath = [model '/' block_name];
    fprintf('\nBlock [%s]:\n', block_name);
    try
        dp = get_param(bpath, 'DialogParameters');
        fnames = fieldnames(dp);
        fprintf('  Available Parameters (%d): %s\n', length(fnames), strjoin(fnames(1:min(12, length(fnames))), ', '));
        for i = 1:min(8, length(fnames))
            fn = fnames{i};
            try
                val = get_param(bpath, fn);
                if ischar(val) || isstring(val)
                    if length(val) > 40
                        val = [val(1:37) '...'];
                    end
                    fprintf('    %s = %s\n', fn, val);
                end
            catch
            end
        end
    catch ME
        fprintf('  Could not get parameters: %s\n', ME.message);
    end
end
