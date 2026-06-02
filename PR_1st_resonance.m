%% MEMS PR Board - Frequency Response Plot
% This script plots:
% 1. Magnitude Response (dB)
% 2. Phase Response (deg)
% from Digilent WaveForms Network Analyzer CSV export

clear;
clc;
close all;

%% Import CSV Data
filename = 'digilent_PR.csv';

% Skip Digilent header lines
opts = detectImportOptions(filename);
opts.DataLines = [17 Inf];

data = readtable(filename, opts);

%% Extract Data
freq  = data{:,1};   % Frequency (Hz)
mag   = data{:,2};   % Magnitude (dB)
phase = data{:,3};   % Phase (deg)

%% Unwrap Phase
% Convert to radians -> unwrap -> convert back to degrees
phase_unwrapped = rad2deg(unwrap(deg2rad(phase)));

%% Find Resonance Frequency
[peakMag, idx] = max(mag);
resFreq = freq(idx);
resPhase = phase_unwrapped(idx);

%% Figure 1 - Magnitude Response
figure;

plot(freq/1000, mag, ...
    'LineWidth', 1.5);

hold on;

% Mark resonance peak
plot(resFreq/1000, peakMag, ...
    'ro', ...
    'MarkerSize', 8, ...
    'LineWidth', 2);

grid on;

xlabel('Frequency (kHz)');
ylabel('Magnitude (dB)');
title('PR MEMS Board Frequency Response');

% Match Digilent view
xlim([50 60]);
ylim([-90 10]);

% Annotate resonance frequency
text(resFreq/1000, peakMag, ...
    sprintf('  Resonance = %.3f kHz', resFreq/1000), ...
    'FontSize', 10);

%% Figure 2 - Phase Response
figure;

plot(freq/1000, phase_unwrapped, ...
    'LineWidth', 1.5);

hold on;

% Mark resonance point
plot(resFreq/1000, resPhase, ...
    'ro', ...
    'MarkerSize', 8, ...
    'LineWidth', 2);

grid on;

xlabel('Frequency (kHz)');
ylabel('Phase (deg)');
title('PR MEMS Board Phase Response');

% Match Digilent view
xlim([50 60]);
ylim([-180 180]);

% Annotate resonance frequency
text(resFreq/1000, resPhase, ...
    sprintf('  Resonance = %.3f kHz', resFreq/1000), ...
    'FontSize', 10);

%% Console Output
fprintf('-----------------------------------\n');
fprintf('PR MEMS Resonance Analysis\n');
fprintf('-----------------------------------\n');
fprintf('Resonance Frequency : %.3f kHz\n', resFreq/1000);
fprintf('Peak Magnitude      : %.2f dB\n', peakMag);
fprintf('Phase at Resonance  : %.2f deg\n', resPhase);
fprintf('-----------------------------------\n');