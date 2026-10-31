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
