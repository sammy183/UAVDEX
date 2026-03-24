# UAV DEsign eXploration
## IN PROGRESS: April 2026 is the target for public release

## Installation
Anaconda is recommended. In the desired environment, simply run:
```
pip install uavdex
```

## UAVDEX usage<h3>
by Sammy N. Nassau, RPI DBF 2021-2026

## PointDesign
This object allows for determination of electric aircraft propulsion with specified components across the entire flight envelope.

The 4 key inputs are freestream velocity over the propeller ($U_{\infty}$), altitude ($h$), throttle setting ($\delta T$), and battery state of charge (SOC).

Altitude (in meters) determines the air density ($\rho$). $\rho$ can also be input directly. 

Battery SOC (typically input as decimal from 0-1), can instead by specified by cell voltage ($V_{oc}$), or runtime ($t$, in seconds) assuming constant current. Using runtime, $t$, is acceptable when designing an aircraft that spends most of its flight time in a single condition (i.e. cruise).

To initialize components:
```
import uavdex as ud

design = ud.PointDesign() 			   # initialize PointDesign object
design.Motor('C-4130/20', nmot = 2)    # add a motor, and specify the # of motors
design.Battery('Gaoneng_8S_3300')      # add a battery 
design.Prop('16x10E')                  # add a propeller
```
To view the databases (editable CSV sheets) for motors and batteries, call
```
design.OpenMotorData()
design.OpenBatteryData()
```
and the CSV sheets will be opened by your default system viewer.

All values needed are typically available online, meaning users can add whatever components they desire.

### PointResult
The simplist function to get propulsion quantities (called 'propQ' in the code).

To run:
```
import uavdex as ud

# Component Initialization
design = ud.PointDesign() 			   # initialize PointDesign object
design.Motor('C-4130/20', nmot = 2)    # add a motor, and specify the # of motors
design.Battery('Gaoneng_8S_3300')      # add a battery 
design.Prop('16x10E')                  # add a propeller

# PointResult
# Uinf:	velocity in m/s
# dT: 	throttle (0-1)
# h: 	altitude in m 
# t: 	runtime in s
design.PointResult(Uinf = 15, dT = 0.7, h = 50, t =30)
```
which prints the following to the console:
> At Uinf = 15.0 m/s, Throttle = 70%, Density = 1.219 kg/m<sup>3</sup>, Runtime = 30.0 s  
> Total Thrust (N)               = 50.254  
> Total Torque (Nm)              = 1.776  
> RPM                            = 6251.107 \
> Drive Efficiency               = 38.44% \
> Propeller Efficiency           = 64.82% \
> Gearing Efficiency             = 100.00% \
> Motor Efficiency               = 91.52% \
> ESC Efficiency                 = 65.10% \
> Battery Efficiency             = 99.52% \
> Mech. Power Out of 1 Motor (W) = 581.428 \
> Elec. Power Into 1 Motor (W)   = 635.293 \
> Elec. Power Into 1 ESC (W)     = 975.872 \
> Waste Power in 1 Motor (W)     = 53.865 \
> Waste Power in 1 ESC (W)       = 340.579 \
> Waste Power in 1 Battery (W)   = 9.506  
> Current in 1 Motor (A)         = 28.674  
> Current in 1 ESC (A)           = 30.832  
> Current in Battery (A)         = 61.664  
> Voltage in 1 Motor (V)         = 22.156  
> Voltage in 1 ESC (V)           = 31.651 \
> Battery Voltage (V)            = 31.651 \
> Voltage Per Cell (V)           = 3.976 \
> State of Charge                = 84.43%

### LinePlot
To automate a *sweep* of any of the 4 variables, use a LinePlot.
The propQ options (corresponding to the PointResult output) are:
```
'T', 'Q', 'RPM', 'eta_drive', 'eta_p', 'eta_g', 'eta_m', 'eta_c', 'eta_b', 'Pout', 'Pin_m', 'Pin_c', 'Pw_m', 'Pw_c', 'Pw_b', 'Im', 'Ic', 'Ib', 'Vm', 'Vc', 'Vb', 'Voc', 'SOC'
```
which must be input as 
```
propQ = 'T'
```
or 
```
propQ = ['T', 'eta_drive', 'Ib']
```
to plot multiple propQs for the same sweep.

To run:
```
import uavdex as ud
import numpy as np

# Component Initialization
design = ud.PointDesign() 				# initialize PointDesign object
design.Motor('C-4130/20', nmot = 2)		# add a motor, and specify the # of motors
design.Battery('Gaoneng_8S_3300') 		# add a battery 
design.Prop('16x10E') 					# add a propeller

# LinePlot usage
design.LinePlot(propQ = ['T','eta_drive','Ib'], Uinf = np.linspace(0, 50), dT = 1.0, h = 100, t = 30)
```
<table>
	<tr>
		<td width="33%" valign="top">
			<p align="center">
				<a></a>
			</p>
			<img src="./Examples/LinePlot_V_T.png" alt="Thrust">
		</td>
		<td width="33%" valign="top">
			<p align="center">
				<a></a>
			</p>
			<img src="./Examples/LinePlot_V_eta.png" alt="Propulsion Efficiency">
		</td>
		<td width="33%" valign="top">
			<p align="center">
				<a></a>
			</p>
			<img src="./Examples/LinePlot_V_Ib.png" alt="Battery Current">
		</td>
	</tr>
</table>

np.linspace simply samples 50 points by default between the start and ending values. To sample 200 points and get a smoother curve, use 
```
Uinf = np.linspace(0, 50, 200)
```
Alternatively, Uinf can be set to a specific value and sweeps of another quantity (dT, h/rho, or SOC/Voc/t) used.


### ContourPlot
For automation of sweeps of two variables, use a contour plot!
```
import uavdex as ud
import numpy as np

# Component Initialization
design = ud.PointDesign() 				# initialize PointDesign object
design.Motor('C-4130/20', nmot = 2)		# add a motor, and specify the # of motors
design.Battery('Gaoneng_8S_3300') 		# add a battery 
design.Prop('16x10E') 					# add a propeller

# ContourPlot (sweeps of velocity and runtime)
design.ContourPlot(propQ = ['T', 'eta_drive', 'Ib'],
                   Uinf = np.linspace(0, 80, n), 
                   t = np.linspace(0, 300, n),
                   dT = 1.0, 
                   h = 100)
```
<table>
	<tr>
		<td width="33%" valign="top">
			<p align="center">
				<a></a>
			</p>
			<img src="./Examples/ContourPlot_V_t_T.png" alt="Thrust">
		</td>
		<td width="33%" valign="top">
			<p align="center">
				<a></a>
			</p>
			<img src="./Examples/ContourPlot_V_t_eta.png" alt="Propulsion Efficiency">
		</td>
		<td width="33%" valign="top">
			<p align="center">
				<a></a>
			</p>
			<img src="./Examples/ContourPlot_V_t_Ib.png" alt="Battery Current">
		</td>
	</tr>
</table>

<!--
### Primary Objects:

#### PointDesign
PointDesign is the primary method for electric


#### DesignStudy
#### ClassicalSizing

# Propulsion Models 
--> 

[1]: https://rincon-mora.gatech.edu/publicat/jrnls/tec05_batt_mdl.pdf
[2]: https://www.researchgate.net/profile/Andrew-Gong-2/publication/326263042_Performance_Testing_and_Modeling_of_a_Brushless_DC_Motor_Electronic_Speed_Controller_and_Propeller_for_a_Small_UAV_Application/links/5b52a5c545851507a7b6f581/Performance-Testing-and-Modeling-of-a-Brushless-DC-Motor-Electronic-Speed-Controller-and-Propeller-for-a-Small-UAV-Application.pdf
[3]: https://web.mit.edu/drela/Public/web/qprop/motor1_theory.pdf
[4]: https://www.mdpi.com/2226-4310/11/1/16



