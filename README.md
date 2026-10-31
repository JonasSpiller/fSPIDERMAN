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
- **bug fixes** in the C extension,
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
