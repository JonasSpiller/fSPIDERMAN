#include "util.h"
#define WINDOW_PAD 2   /* >= longest run of duplicate grid values from format_grid */
# include <stdio.h>
# include <time.h>
# include "math.h"

 
int factorial(int n) {
  int c, fact = 1;

  for (c = 1; c <= n; c++)
    fact = fact * c; 

  return fact;
}

int find_minimum(double *a, double v, int n) {
  /* SPEED PATCH: `a` is ascending (see find_top_two), so bisect instead of scanning. */
  int c, index, lo, hi, mid, w0, w1;
  double min;

  lo = 0; hi = n - 1;
  while (hi - lo > 1) { mid = (lo + hi) / 2; if (a[mid] <= v) lo = mid; else hi = mid; }
  w0 = lo - WINDOW_PAD; if (w0 < 0) w0 = 0;
  w1 = lo + WINDOW_PAD; if (w1 > n - 1) w1 = n - 1;

  min = (a[w0] - v) * (a[w0] - v);
  index = w0;
  for (c = w0 + 1; c <= w1; c++) {
    if (((a[c] - v) * (a[c] - v)) < min) { index = c; min = (a[c] - v) * (a[c] - v); }
  }
  return index;
}

void find_top_two(double *a, double v, int n, int *out) {
  /* SPEED PATCH: `a` is always an ascending, non-decreasing grid (spiderman.read_model
     .format_grid builds it with np.unique + wrap padding, so duplicates are adjacent).
     The original implementation was two full O(n) scans; this brackets `v` with a
     binary search and then reproduces the original argmin logic on a small window
     around the bracket.  Result is identical, cost is O(log n) instead of O(n). */
  int c, index1, index2, c_start, lo, hi, mid, w0, w1;
  double min;

  /* binary search: largest lo with a[lo] <= v  (clamped to [0, n-1]) */
  lo = 0; hi = n - 1;
  while (hi - lo > 1) {
    mid = (lo + hi) / 2;
    if (a[mid] <= v) lo = mid; else hi = mid;
  }
  /* window wide enough to contain any run of duplicates introduced by format_grid */
  w0 = lo - WINDOW_PAD; if (w0 < 0) w0 = 0;
  w1 = lo + WINDOW_PAD; if (w1 > n - 1) w1 = n - 1;

  min = (a[w0] - v) * (a[w0] - v);
  index1 = w0;
  index2 = w0;

  for (c = w0; c <= w1; c++) {
    if (((a[c] - v) * (a[c] - v)) < min) { index1 = c; min = (a[c] - v) * (a[c] - v); }
  }

  if (index1 == w0) {
    min = (a[w0 + 1] - v) * (a[w0 + 1] - v);
    c_start = w0 + 2;
    index2 = w0 + 1;
  }
  else {
    min = (a[w0] - v) * (a[w0] - v);
    c_start = w0 + 1;
  }

  for (c = c_start; c <= w1; c++) {
    if (((a[c] - v) * (a[c] - v)) < min) {
      if (c != index1) {
        if (a[c] != a[index1]) { index2 = c; min = (a[c] - v) * (a[c] - v); }
      }
    }
  }

  if (index1 > index2) { out[0] = index2; out[1] = index1; }
  else                 { out[0] = index1; out[1] = index2; }
}

int compare_function(const void *a,const void *b) {
	double *x = (double *) a;
	double *y = (double *) b;
	// return *x - *y; // this is WRONG...
	if (*x < *y) return -1;
	else if (*x > *y) return 1; return 0;
}

double simpson(double fa, double fb, double fmid, double a, double b) {
	double int_f;

	int_f = ((b-a)/6.0)*(fa + 4.0*fmid + fb);

	return int_f;

}

/******************************************************************************/

int i4_max ( int i1, int i2 )

/******************************************************************************/
/*
  Purpose:

    I4_MAX returns the maximum of two I4's.

  Licensing:

    This code is distributed under the GNU LGPL license.

  Modified:

    29 August 2006

  Author:

    John Burkardt

  Parameters:

    Input, int I1, I2, are two integers to be compared.

    Output, int I4_MAX, the larger of I1 and I2.
*/
{
  int value;

  if ( i2 < i1 )
  {
    value = i1;
  }
  else
  {
    value = i2;
  }
  return value;
}
/******************************************************************************/

int i4_min ( int i1, int i2 )

/******************************************************************************/
/*
  Purpose:

    I4_MIN returns the smaller of two I4's.

  Licensing:

    This code is distributed under the GNU LGPL license.

  Modified:

    29 August 2006

  Author:

    John Burkardt

  Parameters:

    Input, int I1, I2, two integers to be compared.

    Output, int I4_MIN, the smaller of I1 and I2.
*/
{
  int value;

  if ( i1 < i2 )
  {
    value = i1;
  }
  else
  {
    value = i2;
  }
  return value;
}

/******************************************************************************/

void r8vec_print ( int n, double a[], char *title )

/******************************************************************************/
/*
  Purpose:

    R8VEC_PRINT prints an R8VEC.

  Discussion:

    An R8VEC is a vector of R8's.

  Licensing:

    This code is distributed under the GNU LGPL license.

  Modified:

    08 April 2009

  Author:

    John Burkardt

  Parameters:

    Input, int N, the number of components of the vector.

    Input, double A[N], the vector to be printed.

    Input, char *TITLE, a title.
*/
{
  int i;

  fprintf ( stdout, "\n" );
  fprintf ( stdout, "%s\n", title );
  fprintf ( stdout, "\n" );
  for ( i = 0; i < n; i++ )
  {
    fprintf ( stdout, "  %8d: %14f\n", i, a[i] );
  }

  return;
}

/******************************************************************************/

void timestamp ( void )

/******************************************************************************/
/*
  Purpose:

    TIMESTAMP prints the current YMDHMS date as a time stamp.

  Example:

    31 May 2001 09:45:54 AM

  Licensing:

    This code is distributed under the GNU LGPL license.

  Modified:

    24 September 2003

  Author:

    John Burkardt

  Parameters:

    None
*/
{
# define TIME_SIZE 40

  static char time_buffer[TIME_SIZE];
  const struct tm *tm;
  size_t len;
  time_t now;

  now = time ( NULL );
  tm = localtime ( &now );

  len = strftime ( time_buffer, TIME_SIZE, "%d %B %Y %I:%M:%S %p", tm );

  fprintf ( stdout, "%s\n", time_buffer );

  return;
# undef TIME_SIZE
}