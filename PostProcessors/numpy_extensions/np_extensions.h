#ifndef np_extensions_INCLUDED
#define np_extensions_INCLUDED


// #include "C:\Python27\include\Python.h"
// #include "C:\Python27\Lib\site-packages\numpy\core\include\numpy\ndarrayobject.h"

// including numpy by a relative path instead of absolute requires
// "include_dirs = [numpy.get_include()])" in setup.py. 
// But this way you don't have to edit this file on every machine. --5.2020 APS
#include <Python.h>
#include "numpy/ndarrayobject.h"
#include <iostream>
#include <math.h>

class NumPyArray_Float
{
 private:
  PyArrayObject* a;

 public:
  NumPyArray_Float () { a=NULL; }
  NumPyArray_Float (int n)                  { create(n); }
  NumPyArray_Float (int n1, int n2)         { create(n1, n2); }
  NumPyArray_Float (int n1, int n2, int n3) { create(n1, n2, n3); }
  NumPyArray_Float (double* data, int n)    { wrap(data, n); }
  NumPyArray_Float (double* data, int n1, int n2) { wrap(data, n1, n2); }
  NumPyArray_Float (double* data, int n1, int n2, int n3) { wrap(data, n1, n2, n3); }
  NumPyArray_Float (PyArrayObject* anrray) { a = anrray; }
  // NOTE: if we here call wrap(a), a seg.fault appear!
  //NumPyArray_Float (PyArrayObject* array) { wrap(a); }

  // the create functions allocates a new array of doubles
  // with prescribed size
  int create (int n);
  int create (int n1, int n2);
  int create (int n1, int n2, int n3);

  // the wrap functions takes an existing array, pointed to by
  // a single double* pointer, and wraps it in a NumPy array

  void wrap (double* data, int n) { 
    int dim1[1]; dim1[0] = n; 
    a = (PyArrayObject*) PyArray_FromDimsAndData(
		1, dim1, PyArray_DOUBLE, (char*) data);
  }

  void wrap (double* data, int n1, int n2) { 
    int dim2[2]; dim2[0] = n1; dim2[1] = n2;
    a = (PyArrayObject*) PyArray_FromDimsAndData(
        2, dim2, PyArray_DOUBLE, (char*) data);
  }

  void wrap (double* data, int n1, int n2, int n3) { 
    int dim3[3]; dim3[0] = n1; dim3[1] = n2; dim3[2] = n3;
    a = (PyArrayObject*) PyArray_FromDimsAndData(
        3, dim3, PyArray_DOUBLE, (char*) data);
  }

  // this wrap function takes a C representation of a NumPy
  // array and wraps in the present C++ class:
  void wrap (PyArrayObject* anrray) { a = anrray; }

  int checktype () const;  // are the entries of type double?
  int checkdim  (int expected_ndim) const;
  int checksize (int expected_size1, int expected_size2=0, int expected_size3=0) const;

  double  operator() (int i) const {
#ifdef INDEX_CHECK
    assert(a->nd == 1 && i >= 0 && i < a->dimensions[0]);
#endif
    return *((double*) (a->data + i*a->strides[0]));
  }
  double& operator() (int i) {
    return *((double*) (a->data + i*a->strides[0]));
  }

  double  operator() (int i, int j) const {
    return *((double*) (a->data + i*a->strides[0] + j*a->strides[1]));
  }
  double& operator() (int i, int j) {
    return *((double*) (a->data + i*a->strides[0] + j*a->strides[1]));
  }

  double  operator() (int i, int j, int k) const {
    return *((double*) (a->data + i*a->strides[0] + j*a->strides[1] +
			k*a->strides[2]));
  }
  double& operator() (int i, int j, int k) {
    return *((double*) (a->data + i*a->strides[0] + j*a->strides[1] +
			k*a->strides[2]));
  }

  int dim() const { return a->nd; }  // no of dimensions
  int size1() const { return a->dimensions[0]; }
  int size2() const { return a->dimensions[1]; }
  int size3() const { return a->dimensions[2]; }
  double* getData () { return (double*) a->data; }  // most useful in 1D
  PyArrayObject* getPtr () { return a; }
};

void dump (std::ostream& o, const NumPyArray_Float& a);

#endif
