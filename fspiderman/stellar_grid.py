# -*- coding: utf-8 -*-
import os.path

use_fitsio = False
try:
    import fitsio
    use_fitsio = True
except:
    from astropy.io import fits
    use_fitsio = False

import matplotlib.pyplot as plt
import numpy as np
import fspiderman

def gen_grid(l1,l2,logg=4.5, response = False, stellar_model = "blackbody", verbose=False):
        #options for stellar models are "blackbody", "PHOENIX", and "path_to_model"
    z = -0.0

    h =6.62607004e-34;          #m^2/kg/s
    c =299792458.0;             #m/s
    kb =1.38064852e-23;         #m^2 kg /s^2 K

    teffs = [2500,3000,3500,4000,4500,5000,5500,6000,6500,7000]

    warned = False

    filter = response
    if response != False:
        filter = fspiderman.get_filter(response)

    totals = []
    for teff in teffs:
        if stellar_model == "PHOENIX":
            if fspiderman.rcParams.read == False: print('Add path to PHOENIX models to .fspidermanrc file')
            wvl, flux = get_phoenix_spectra(teff,logg,z)
            PHOENIX_DIR = fspiderman.rcParams['PHOENIX_DIR']

            if warned == False:
                print('using stellar spectra in '+PHOENIX_DIR)

            if ( ((l1 > np.min(wvl)) & (l1 < np.max(wvl))) & ((l2 > np.min(wvl)) & (l2 < np.max(wvl) )) ):
                totals += [sum_flux(wvl,flux,l1,l2,filter)]
            else:
                if warned == False:
                    print('wavelengths out of bound for stellar model, using blackbody approximation')
                b_wvl = np.linspace(l1,l2,1000)
                b_flux = (2.0*h*(c**2)/(b_wvl**5))*(1.0/( np.exp( (h*c)/(b_wvl*kb*teff) )- 1.0));
                totals += [sum_flux(b_wvl,b_flux,l1,l2,filter)]
        elif stellar_model == "blackbody":
            if warned == False:
                print('no stellar models provided, using blackbody approximation')
            b_wvl = np.linspace(l1,l2,1000)
            b_flux = (2.0*h*(c**2)/(b_wvl**5))*(1.0/( np.exp( (h*c)/(b_wvl*kb*teff) )- 1.0));       #SI units: W/sr/m^3
            totals += [sum_flux(b_wvl,b_flux,l1,l2,filter)]
        else:
            if os.path.isfile(stellar_model):
                spectrum = np.genfromtxt(stellar_model)
                wvl, flux = spectrum[:,0], spectrum[:,1] 
            else: print("Model stellar spectrum file", stellar_model, "not found")

            if ( ((l1 > np.min(wvl)) & (l1 < np.max(wvl))) & ((l2 > np.min(wvl)) & (l2 < np.max(wvl) )) ):
                totals += [sum_flux(wvl,flux,l1,l2,filter)]
            else:                    
                if warned == False:
                    print('wavelengths out of bound for stellar model, using blackbody approximation')
                b_wvl = np.linspace(l1,l2,1000)
                b_flux = (2.0*h*(c**2)/(b_wvl**5))*(1.0/( np.exp( (h*c)/(b_wvl*kb*teff) )- 1.0));
                totals += [sum_flux(b_wvl,b_flux,l1,l2,filter)]
        warned = True


    teffs = np.array(teffs)
    totals = np.array(totals)

    return [teffs, totals]

def sum_flux(wvl, flux, l1, l2, filter=False):
    """In-band stellar flux: trapezoid of (response x flux) over exactly [l1, l2].

    The band edges are added as interpolated samples, so no spectrum sample is dropped and the integral covers the
    same closed interval as bb_flux() in c_src/blackbody.c, which integrates the planet's blackbody over [l1, l2].
    Upstream used the strict mask (wvl > l1) & (wvl < l2) with rectangle weights, which dropped both band-edge
    samples and left the stellar flux short by ~dlambda * [B(l1) + B(l2)] / 2 (0.22% for a 5-12 um top-hat at
    1000 samples), scaling every Fp/Fs up by the same factor."""
    wvl, flux = np.asarray(wvl, float), np.asarray(flux, float)
    inside = (wvl > l1) & (wvl < l2)
    w = np.concatenate(([l1], wvl[inside], [l2]))
    f = np.concatenate(([np.interp(l1, wvl, flux)], flux[inside], [np.interp(l2, wvl, flux)]))
    if filter is not False:
        fw, fr = np.asarray(filter[0], float), np.asarray(filter[1], float)
        o = np.argsort(fw)
        fw, fr = fw[o], fr[o]
        # Guard: a band edge outside the tabulated response is a real error -- except for round-off. A response file
        # written with ~11 significant digits can sit ~1e-11 (relative) inside the in-memory edge it was built from, and
        # since the band edges are evaluated exactly (above), that alone used to raise. Edges within the tolerance are
        # evaluated with the response held at its first/last tabulated value (np.interp does this).
        tol = 1e-9 * fw[-1]
        if l1 < fw[0] - tol or l2 > fw[-1] + tol:
            raise ValueError(f"band [{l1:.10e}, {l2:.10e}] m extends beyond the filter response "
                             f"[{fw[0]:.10e}, {fw[-1]:.10e}] m")
        r = np.interp(w, fw, fr)
    else:
        r = np.ones_like(w)
    trapezoid = getattr(np, "trapezoid", None) or np.trapz
    return float(trapezoid(r * f, w))

def get_phoenix_spectra(teff,logg,z):
    ftemplate = 'lte{teff:05d}-{logg:4.2f}{z:+3.1f}.PHOENIX-ACES-AGSS-COND-2011-HiRes.fits'

    PHOENIX_DIR = fspiderman.rcParams['PHOENIX_DIR']

    filename = os.path.join(PHOENIX_DIR,ftemplate.format(teff=teff,logg=logg,z=z))

    # changing to si, W / m^3 / str
    if use_fitsio:
        flux,h = fitsio.read(filename, ext=0, header=True)
    else:
        flux,h = fits.getdata(filename, ext=0, header=True)
    
    flux = flux*1e-7*1e6/(np.pi)

    crval = h['CRVAL1']
    cdelt = h['CDELT1']
    ctype = h['CTYPE1']

    if ctype == 'AWAV-LOG':
        wvl = (np.exp(crval + cdelt*np.arange(0,len(flux))))*1e-10
    else:
        print('ctype is not log! It  is {}'.format(ctype))

    return wvl, flux
