# Template_bank_generator_codes_for_PULSEJET_beta
Codes to generate Random template banks to use as input for PULSEJET_beta polynomial template bank based jerk search version of Peasoup. 

It uses the acceleration and Jerk phase space model 

$\phi(t)=2\pi f\left(t - \frac{a t^2}{2c} - \frac{j t^3}{6c}\right)$


Just copy paste the generator code and adjust the parameters as required.

# ===== User parameters =====
f        = 230.0      # Hz
T        = 600.0      # s
a_max    = 150.0      # m/s^2
j_max    = 30.0       # m/s^3
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
