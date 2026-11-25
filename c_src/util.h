int find_minimum(double *a, double v, int n);
void find_top_two(double *a, double v, int n, int *out);
int compare_function(const void *a,const void *b);
double simpson(double fa, double fb, double fmid, double a, double b);
int i4_max ( int i1, int i2 );
int i4_min ( int i1, int i2 );
void r8vec_print ( int n, double a[], char *title );
void timestamp ( void );
int factorial (int n);
/* ERROR PATCH: C routines record an error here instead of calling exit(0), which ended the Python process
   with status 0; the entry points in _web.c raise it as a ValueError. */
extern char spiderman_error[256];
void set_spiderman_error(const char *format, ...);
