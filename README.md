# fSPIDERMAN

A fork of **SPIDERMAN** (Louden & Kreidberg 2018, MNRAS 477, 2613,
[doi:10.1093/mnras/sty558](https://doi.org/10.1093/mnras/sty558);
upstream: [github.com/tomlouden/SPIDERMAN](https://github.com/tomlouden/SPIDERMAN)),
the open-source code for modelling secondary eclipses and phase curves of exoplanets.
If you use it, cite the SPIDERMAN paper; the original documentation is at
[spiderman.readthedocs.io](http://spiderman.readthedocs.io).

This fork is maintained for **HyperPhase**
([github.com/JonasSpiller/ExoPhase](https://github.com/JonasSpiller/ExoPhase)), an MSc thesis
project (ETH Zürich / Harvard) on the nightside temperatures of tidally locked rocky exoplanets,
whose thermal forward model drives SPIDERMAN's `direct_T` brightness model with custom
(hyper-illumination) temperature maps inside fitting and MCMC loops. Upstream SPIDERMAN
(last commit Aug 2020) does not build or run on a modern scientific-Python stack, and its
`lightcurve()` routine is the runtime bottleneck of that work. The fork therefore carries

- **compatibility fixes** so it builds and runs on current Python / numpy / matplotlib / setuptools,
- **bug fixes** in the C extension and in the stellar-flux integration,
- **performance patches** to `lightcurve()`, with output unchanged,

each applied as its own commit and documented below. The physics is untouched: a patched build
reproduces the upstream light curves bit for bit, except where a fix changes a result on purpose,
which is then stated.

The package is renamed to **`fspiderman`** (`import fspiderman as sp`, same API) so it can coexist
with an unmodified `spiderman` in the same environment.

## Patches

Base: upstream commit `379a5b6` (Aug 2020).

### 1. Version fixes (`apply version patch`)

Stock `spiderman-package` 1.0.3 predates modern scientific Python. The PyPI wheel's precompiled
C extension is **ABI-incompatible with numpy ≥ 2** (any non-constant `direct_T` brightness grid
yields garbage temperatures or segfaults inside the bicubic-spline routines), and building the
Aug-2020 source from scratch fails on a current stack for several independent reasons.

Six small changes, none touching the physics, make it **build and run on a modern stack**
(tested on Python 3.11 / numpy 2.4.6 / matplotlib 3.10 / setuptools 82):

- `setup.py`: `license` must be a string, not a list (modern setuptools calls `.split()` on it);
- `setup.py`: drop the unused `import numpy.distutils.misc_util` (`numpy.distutils` was removed in numpy 2.0 and breaks setuptools ≥ 72);
- `c_src/_web.c`, `c_src/_heron.c`: `NPY_IN_ARRAY → NPY_ARRAY_IN_ARRAY` (39×; the old flag alias is gone from the numpy 2.x headers);
- `fspiderman/plot.py`: `matplotlib._png.read_png → matplotlib.image.imread` (private module removed in matplotlib 3.3);
- `fspiderman/read_model.py`: `np.array([LO, LA, T]) → np.array([LO, LA, T], dtype=object)` (ragged arrays need an explicit object dtype since numpy 1.24);
- `fspiderman/stellar_grid.py`: de-list the boolean mask `[(…)] → (…)` (indexing with a list containing a boolean array is an error in modern numpy).

Verified after the rebuild: a constant-temperature `direct_T` grid is bit-for-bit identical to the
`two temperature` model with equal day/night temperatures, and repeated `lightcurve()` calls
return identical results.

The same commit series also adds a `pyproject.toml` declaring the build requirements
(`setuptools`, `wheel`, `numpy>=2`), so a plain `pip install .` works with pip's default isolated
build (upstream needs `--no-build-isolation`, because `setup.py` imports numpy for its C headers
without declaring it). `numpy>=2` guarantees the extension is compiled against numpy-2 headers,
the ABI it is run with. The install itself is the usual
`pip install git+https://github.com/JonasSpiller/fSPIDERMAN.git` or `pip install .` from a clone.

### 2. Speed patch (`apply speed patch`)

`lightcurve()` is the runtime bottleneck of any fit or MCMC built on SPIDERMAN, above all for
the `direct_T` model, which interpolates a user-supplied temperature map for every planet segment
at every time step. Four C-level changes, none touching the physics, remove redundant work in
those inner loops:

1. binary-search the ascending brightness grid instead of two O(*n*) linear scans (`util.c`);
2. precompute the 16 bicubic coefficients **once per grid cell** instead of once per
   (segment × time-step), and drop the per-call heap churn (`bicubic.c`, `web.c`, `generate.c`);
3. reentrant mapping routines that write into stack buffers instead of `malloc`/`free`
   (`generate.c`, `orthographic.c`);
4. direct interval index for the uniform blackbody spline grid, no search (`blackbody.c`, `spline.c`).

Net effect: **`lightcurve()` runs ~4–5× faster** (measured 4.56× for a `direct_T`, `N_LAYERS = 60`,
`len(t) = 1000` curve on Apple Silicon), with output **bit-for-bit identical** to upstream except a
≤ 0.04 ppm float-rounding difference on the bicubic path at sharp terminators, about 25× below the
`N_LAYERS` truncation error there and negligible against JWST noise. With `nearest = True` the
output is bit-identical and the speed-up reaches ~6×, since the bicubic evaluation is skipped
entirely.

### 3. Memory-leak fix (`apply memoryleak patch`)

`c_src/_web.c › web_lightcurve`, the C entry point behind `p.lightcurve()`, allocates a
2 × `n_wvls` `wvl_grid` on every call, frees the two rows but never the outer pointer array: a
small per-call leak (~32 B/call; macOS `leaks` reports 80 leaked blocks after 80 `direct_T` calls).
The `direct_T` grid clean-up also carried latent undefined behaviour: `free(T_2d[0])` released
numpy-owned data, and `Py_DECREF` was applied to raw `double*` data pointers and to borrowed
argument objects.

The fix adds the missing `free(wvl_grid)` and replaces the grid clean-up with the numpy-correct
counterpart of `PyArray_AsCArray` (`PyArray_Free` on the converted grid, `Py_DECREF` on the two
`PyArray_FROM_OTF` references, which are hoisted to function scope for that purpose).

The edits run only after the light curve is computed, so the output is **bit-for-bit identical**;
`leaks` drops to 0 blocks. This does not cure the tens-of-MB RSS growth seen in very long sweeps,
which is allocator-arena behaviour rather than a leak and occurs with or without this patch.

### 4. Bicubic clamp (`apply bicubic clamp patch`)

The `direct_T` model evaluates the temperature map with a bicubic interpolant (`bcuint` /
`bcuint_fast` in `c_src/generate.c`, gradients from finite differences). A bicubic is not
monotone: at a sharp step in the map it overshoots on both sides. For a map with a 0 K nightside
next to a ~1000–3000 K terminator the undershoot reaches tens of kelvin below the nightside value
(46 K for a TOI-2431 b naive-insolation map, 103 K at a/R★ = 1.5, T★ = 6000 K, A_B = 0), and
`bb_interp()` in `c_src/blackbody.c` then hits `if (tval < 0) exit(0)` — the infamous
"CANNOT DO NEGATIVE TEMPERATURES!", a hard process kill rather than a Python exception. The usual
workaround, flooring the map at 100–200 K, is not free at long wavelengths: a 200 K floor adds
~1.8 ppm of spurious nightside flux at 18 µm for a TOI-2431 b-like planet.

The fix clamps the interpolated value to the range of the cell's four corner values, right after
the bicubic evaluation. It is exact at the nodes, removes the overshoot in both directions, leaves
`nearest = True` untouched (that path bypasses the bicubic), and affects a smooth map only where
it has an extremum strictly inside a cell, at the 10⁻³ ppm level.

Verified against the unclamped build: constant maps, `nearest = True` and the analytic Louden
model are bit-identical; smooth hyper-illumination curves change by ≤ 0.001 ppm and naive curves
at the same floor by ≤ 0.013 ppm; a step-map test whose exact answer is known (half the disc at
quadrature) becomes 2–15× **more** accurate; maps with a 0 K nightside now run and give exactly
zero nightside flux edge-on; a representative albedo fit shifts by 5 × 10⁻⁵; no measurable
slowdown. **This is the one patch that deliberately changes results** (removing an interpolation
artefact), so curves from a clamped build are not bit-identical to upstream at sharp terminators.

### 5. Stellar band-flux fix (`fix stellar band flux`)

SPIDERMAN's Fp/Fs is the ratio of two band integrals computed in two different places. The planet
side is integrated in C (`bb_flux` in `c_src/blackbody.c`, Simpson's rule over the closed interval
[l1, l2]). The stellar side comes from Python: `stellar_grid.gen_grid` samples the stellar spectrum
(a blackbody on `np.linspace(l1, l2, 1000)`, or a PHOENIX / user spectrum) and `sum_flux` integrates it
with the strict mask `(wvl > l1) & (wvl < l2)` and rectangle weights. That drops **both band-edge
samples**, so the stellar flux is short by ≈ Δλ·[B(l1) + B(l2)]/2 and every thermal Fp/Fs comes out
too high by a band-dependent factor: **0.216 %** for a 5–12 µm top-hat, 0.09 % for MIRI/LRS or
NIRSpec G395H NRS1, 0.02 % for NRS2, 0.05–0.07 % for the MIRI imaging filters (the factor is the same
at every planet temperature, so it rescales the whole thermal curve).

The fix makes `sum_flux` a trapezoid of (response × flux) over exactly [l1, l2], adding the two band
edges as interpolated samples. For the blackbody star this agrees with an adaptive quadrature of the
Planck function to < 10⁻⁶; the stellar T_eff spline in `web.c` (500 K nodes) and the planet-side
`bb_grid` spline (100 K nodes) were checked at the same time and contribute < 10⁻⁵. **Like the clamp,
this patch deliberately changes results:** all thermal Fp/Fs values drop by the factors above.

Found while comparing against Alex McGinty's independent bare-rock phase-curve model: with an exact 1D
reference integral for the occultation depth, the remaining SPIDERMAN error after this fix is the **midpoint disc
quadrature** of `generate_planet` (uniform radial layers, brightness evaluated at the segment centre),
which converges only as ~`n_layers`^-1.5 because the brightness has infinite radial slope at the limb:
+0.16 / +0.06 / +0.02 / +0.007 ppm on a 240 ppm depth for 40 / 80 / 160 / 320 layers, independent of
the temperature-map resolution. This is left as is; use `n_layers ≥ 80` where absolute depths matter.

### 6. Photon-counting response weighting (`fix filter photon weighting`)

With a response file, SPIDERMAN weights the energy spectral radiance $B_\lambda$ of planet (`bb_flux`,
`c_src/blackbody.c`) and star (`stellar_grid.sum_flux`) with the tabulated response. The files that
`get_filter` reads follow the SVO / Pandeia convention, electrons per incident photon, so a photon-counting
detector's signal is $\int R(\lambda)\,B_\lambda\,\lambda/(hc)\,d\lambda$: one photon carries $hc/\lambda$,
hence the per-photon response becomes a per-energy one by **multiplying** with $\lambda/hc$. Upstream's
`get_filter` **divided** by $\lambda$ instead (`hc*R/wvl`, commented as "energy density instead of photon
number"), tilting every band by $\lambda^2$. The fix is the one line `R * wvl / hc`; the planet and the
star are weighted the same way, so the dimensionless constant drops out of $F_p/F_s$.

The tilt is not small for wide bands. Change of $F_p/F_s$ (fix vs upstream) for a blackbody planet around
a 4100 K star, with the JWST throughputs used in HyperPhase:

| band | 900 K planet | 1500 K planet |
|---|---|---|
| MIRI/LRS 5-10.5 | +10.7 % | +4.6 % |
| NIRSpec NRS2 | +3.2 % | +1.4 % |
| NIRSpec NRS1 | +3.1 % | +1.4 % |
| MIRI/F1500W | +0.3 % | +0.2 % |

Until this fix, HyperPhase worked around the inversion by storing its response files pre-multiplied with
$\lambda^2$ (so that $hc\,R\lambda^2/\lambda \propto R\lambda$), which gave the correct weighting but files
that were not throughputs. With the fix the files are plain throughputs again and the pipeline's results
are unchanged (verified to rounding level). `filter = False` (top-hat) is untouched and still integrates
energy, as documented upstream.

## Known issues and usage notes

- **`p.eclipse_depth()` segfaults with `brightness_model="direct_T"`** (heap corruption in the C
  extension, unpatched). Measure the occultation depth from the light curve instead: out-of-occultation
  flux minus in-occultation flux.
- **`direct_T` grid orientation.** Build the map with `format_grid(LO, LA, T.T)` from `indexing='ij'`
  meshgrids in degrees and the temperature array transposed to longitude-first. A wrong orientation does
  not raise, it silently produces a rotated planet.
- **Sorted grids.** The longitude/latitude vectors must be ascending (see patch 2).
- **Hard process exits.** "PLANET IS INSIDE STAR" (a/R★ ≲ 1 + R_p/R★) and, on unpatched builds,
  "CANNOT DO NEGATIVE TEMPERATURES" are `exit(0)` calls in the C code, not Python exceptions: a bad
  proposal in a fitting loop kills the worker process. Reject such geometries in the prior.

