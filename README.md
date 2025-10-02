# Template_bank_generator_codes_for_PULSEJET_beta
Codes to generate Random template banks to use as input for PULSEJET_beta polynomial template bank based jerk search version of Peasoup. 

It uses the acceleration and Jerk phase space model 

$\phi(t)=2\pi f\left(t - \frac{a t^2}{2c} - \frac{j t^3}{6c}\right)$


What the code does (briefly)

Build the metric from the phase model
Compute the 2×2 projected metric on 
(
𝑎
,
𝑗
)
(a,j). Its determinant defines a local volume element; larger values mean we need denser templates there.

Estimate proper volume & template count
Monte-Carlo over the 
(
𝑎
,
𝑗
)
(a,j) box gives the proper volume. Using your target coverage and mismatch, the code estimates how many templates you need.

Generate the bank (two interchangeable samplers)

Metropolis–Hastings (independence sampler):
Proposes points uniformly in a slightly padded box and accepts them in proportion to the local density derived from the metric. Trims to the target box.
Simple and fast for small/medium banks.

emcee ensemble sampler:
Runs a Goodman–Weare affine-invariant MCMC with a log-density from the metric. Produces many low-correlation samples efficiently, then downsamples to the exact size.
Robust and scalable for large banks.

Validate coverage
The notebook checks nearest-template mismatch on random test points and plots a coarse coverage map—so you can see if the bank meets your mismatch goal and whether edges are covered well.

When to use which sampler

Use Metropolis–Hastings for light banks (roughly ≤ 20k templates). It’s lightweight, dependency-free, and converges quickly with global proposals.

Use emcee for larger banks (≫ 20k). The ensemble sampler explores the density more efficiently and yields better-mixed samples with fewer tuning knobs.


Just copy paste the generator code and adjust the parameters as required.

# ===== User parameters =====
f        = 230.0      # Hz (spin frequency of the pulsar)
T        = 600.0      # s  (Length of the observation file)
a_max    = 150.0      # m/s^2  (max_acceleration you want to account for goes from +a_max to -a_max)
j_max    = 30.0       # m/s^3  (max_Jerk you want to account for goes from +j_max to -j_max)
coverage = 0.90       # desired coverage
mismatch = 0.30       # target μ
nmc      = 200_000    # MC samples for volume estimate
pad_frac = 0.15       # edge padding for generation
c        = 3.0e8


For lighter template banks, using Metropolis hastings generator is suggest and for heavy template banks the emcee generator is suggested. You can toggle between the versions by using the flag 
# Choose sampler: emcee for large banks, independence-MH for small banks
use_emcee = False

Use true to switch of the emcee sampler. 

The code when run in colab will provide diagnostic plots to check your template banks for coverage and mismatch. 

<img width="523" height="393" alt="image" src="https://github.com/user-attachments/assets/4383df16-58cc-456d-b5c6-0119b54eba99" />

<img width="544" height="470" alt="image" src="https://github.com/user-attachments/assets/3a72e007-a1fd-44aa-b6f8-168300160e42" />

You can visually inspect your template banks using these. 
