/* Found in 
http://vefur.simula.no/~hpl/scripting/src/py/mixed/Grid2D/C++/plain/
*/

#include "np_extensions.h"


int NumPyArray_Float:: checktype () const
{
  if (a->descr->type_num != PyArray_DOUBLE) {
    PyErr_Format(PyExc_ValueError,
		 "a is not of type 'Float'");
    return 0;
  }
  return 1;
}

int NumPyArray_Float:: checkdim (int expected_ndim) const
{
  if (a->nd != expected_ndim) {
    PyErr_Format(PyExc_ValueError,
		 "NumPy array is %d-dimensional; expected %d dimensions", 
		 a->nd, expected_ndim);
    return 0;
  } 
  return 1;
}

int NumPyArray_Float:: checksize (int expected_size1, 
				  int expected_size2, 
				  int expected_size3) const
{
  if (a->dimensions[0] != expected_size1) {
    PyErr_Format(PyExc_ValueError,
		 "NumPy array's 1st index runs from 0 to %d (expected %d)", 
		 a->dimensions[0], expected_size1);
    return 0;
  }
  if (expected_size2 > 0) {
    if (a->dimensions[1] != expected_size1) {
	PyErr_Format(PyExc_ValueError,
		     "NumPy array's 2nd index runs from 0 to %d (expected %d)", 
		     a->dimensions[1], expected_size2);
	return 0;
    }
    if (expected_size3 > 0) {
      if (a->dimensions[2] != expected_size3) {
	PyErr_Format(PyExc_ValueError,
		     "NumPy array's 3rd index runs from 0 to %d (expected %d)", 
		     a->dimensions[2], expected_size3);
	return 0;
      }
    }
  }
  return 1;
}


int NumPyArray_Float:: create (int n) 
{ 
  printf("Creating array(%d)\n", n);
  int dim1[1]; dim1[0] = n; 
  a = (PyArrayObject*) PyArray_FromDims(1, dim1, PyArray_DOUBLE);
  if (a == NULL) { 
    printf("creating NumPyArray in C failed, dim=(%d)\n", n);
    return 0;
  }
  return 1;
}

int NumPyArray_Float:: create (int n1, int n2) 
{ 
  printf("Creating array(%d,%d)\n", n1, n2);
  int dim2[2]; dim2[0] = n1; dim2[1] = n2;
  a = (PyArrayObject*) PyArray_FromDims(2, dim2, PyArray_DOUBLE);
  if (a == NULL) { 
    printf("creating a failed, dims=(%d,%d)\n",n1, n2);
    return 0;
  }
  return 1;
}

int NumPyArray_Float:: create (int n1, int n2, int n3) 
{ 
  int dim3[3]; dim3[0] = n1; dim3[1] = n2; dim3[2] = n3;
  a = (PyArrayObject*) PyArray_FromDims(3, dim3, PyArray_DOUBLE);
  if (a == NULL) { 
    printf("creating a failed, dims=(%d,%d,%d)\n",n1, n2, n3);
    return 0;
  }
  return 1;
}

void dump (std::ostream& o, const NumPyArray_Float& a)
{
  int i,j,k;
  o << "Dump of NumPyArray object:\n";
  if (a.dim() == 1) {
    for (i = 0; i < a.size1(); i++) {
      o << "(" << i << ")=" << a(i) << " ";
      if (i % 6 == 0) { o << '\n'; }
    }
  }
  if (a.dim() == 2) {
    for (i = 0; i < a.size1(); i++) {
      for (j = 0; j < a.size2(); j++) {
	o << "(" << i << "," << j << ")=" << a(i,j) << " ";
	if (i % 5 == 0) { o << '\n'; }
      }
    }
  }
  if (a.dim() == 3) {
    for (i = 0; i < a.size1(); i++) {
      for (j = 0; j < a.size2(); j++) {
	for (k = 0; k < a.size3(); k++) {
	  o << "(" << i << "," << j << "," << k << ")=" << a(i,j,k) << " ";
	  if (i % 4 == 0) { o << '\n'; }
	}
      }
    }
  }
}


/* -----------------  / 
/ Begin Customization /
/ ------------------ */

/* ===== multXbyAI =========
Multiply vector x in place by scalar float a
*/
static PyObject * multXbyAI(PyObject *self, PyObject *args){
	PyArrayObject *x_;
	double a;

	if (!PyArg_ParseTuple(args, "O!d:multXbyAI",
							&PyArray_Type, &x_,
							&a)){
		return NULL;
	};

	NumPyArray_Float x(x_); 
	int nx = x.size1();
	if (!x.checktype()) { return NULL; }
	if (!x.checkdim(1)) { return NULL; }
	
	
	int i;
	for (i=0; i < nx; i++){
		x(i) *= a;
	}

	//Return 1 to signal successful operation
	return Py_BuildValue("i",1);
}


/* ===== multXbyA =========
Multiply vector x by scalar float a, return new vector y
*/
static PyObject * multXbyA(PyObject *self, PyObject *args){
	PyArrayObject *x_;
	double a;

	if (!PyArg_ParseTuple(args, "O!d:multXbyA",
							&PyArray_Type, &x_,
							&a)){
		return NULL;
	};

	NumPyArray_Float x(x_);  int nx = x.size1();
	if (!x.checktype()) { return NULL; }
	if (!x.checkdim(1)) { return NULL; }

	//make new array:
	NumPyArray_Float y(nx);

	
	int i;
	for (i=0; i < nx; i++){
		y(i) = a*x(i);
	}

	//Return new array y
	return PyArray_Return(y.getPtr());
}




/* ===== myMax =========
Find the index of the maximum element in array x
*/
static PyObject * myMax(PyObject *self, PyObject *args){
	PyArrayObject *x_;
	//double a;

	if (!PyArg_ParseTuple(args, "O!:myMax",&PyArray_Type, &x_)){
		return NULL;
	};

	NumPyArray_Float x(x_); 
	int nx = x.size1();
	if (!x.checktype()) { return NULL; }
	if (!x.checkdim(1)) { return NULL; }
	
	
	//Algorithm
	int imax = 0;
	int i = 0;
	double max = x(0);
	for (i=1;i<nx;i++){
		if(x(i)>max){
			max = x(i);
			imax = i;
		}
	}

	//Return Max value
	return Py_BuildValue("(i,d)",imax,max);
}


/* ===== rowMax =========
Find the maximum of each row of matrix mat
*/
static PyObject * rowMax(PyObject *self, PyObject *args){
	PyArrayObject *mat_,*ind_,*max_;

	if (!PyArg_ParseTuple(args, "O!O!O!:rowMax",&PyArray_Type, &mat_,
											    &PyArray_Type, &ind_,
												&PyArray_Type, &max_)){
		return NULL;
	};

	NumPyArray_Float mat(mat_); 
	if (!mat.checktype()) { return NULL; }
	if (!mat.checkdim(2)) { return NULL; }
	int m = mat.size1(); int n = mat.size2();
	
	NumPyArray_Float ind(ind_); 
	int mx = ind.size1();
	if (mx != m) { return NULL; }
	if (!ind.checktype()) { return NULL; }
	if (!ind.checkdim(1)) { return NULL; }

	NumPyArray_Float max(max_); 
	mx = max.size1();
	if (mx != m) { return NULL; }
	if (!max.checktype()) { return NULL; }
	if (!max.checkdim(1)) { return NULL; }
	
	
	//Algorithm
	int i,j;
	for (i=0;i<m;i++){    
		ind(i) = 0;
		max(i) = mat(i,0);
		for (j=1;j<n;j++){
			if(mat(i,j)>max(i)){
				max(i) = mat(i,j);
				ind(i) =  (float) j; //cast as int in Python
			}
		}
	}

	//Return Max value
	return  Py_BuildValue("i",1);
}



/* ===== delta_filt =========
N must be same length as L
first and last (n-1)/2 points of y are invalid
*/
static PyObject * delta_filt(PyObject *self, PyObject *args){
	PyArrayObject *x_,*index_,*win_,*y_;
	int ii_lower,ii_upper;

	if (!PyArg_ParseTuple(args, "O!O!O!O!ll:delta_filt",&PyArray_Type, &x_,
											    &PyArray_Type, &index_,
												&PyArray_Type, &win_,
												&PyArray_Type, &y_,
												&ii_lower, 
												&ii_upper)){
		return NULL;
	};

	NumPyArray_Float x(x_); 
	if (!x.checktype()) { return NULL; }
	if (!x.checkdim(1)) { return NULL; }
	int nx = x.size1();
	
	NumPyArray_Float index(index_); 
	int nindex = index.size1();
	if (!index.checktype()) { return NULL; }
	if (!index.checkdim(1)) { return NULL; }

	NumPyArray_Float win(win_); 
	int nwin = win.size1();
	if (nindex != nwin) { return NULL; }
	if (!win.checktype()) { return NULL; }
	if (!win.checkdim(1)) { return NULL; }

	NumPyArray_Float y(y_); 
	int ny = y.size1();
	if (!y.checktype()) { return NULL; }
	if (!y.checkdim(1)) { return NULL; }
	
	
	//Algorithm 
	int i,j,i_tmp;
	double f0;
	double sum_win = 0.0;
	for(j=0;j<nwin;j++){
		sum_win += win(j);
	}
	for(i = ii_lower; i < ii_upper;i++){
		f0 = y(i);//f0 encoded in y, save here before corrupt
		y(i) = 0;
		for (j=0;j<nwin;j++){
			i_tmp = i - ((int) floor(index(j)/f0+.5));
			y(i)+=(x(i_tmp)*win(j));
		};
		y(i) /= sum_win;
	};


	//Return Max value
	return  Py_BuildValue("i",1);
}

/* ===== firstPos =========
find index of first positive entry
*/
static PyObject * firstPos(PyObject *self, PyObject *args){
	PyArrayObject *x_;

	if (!PyArg_ParseTuple(args, "O!:firstPos",&PyArray_Type, &x_)){
		return NULL;
	};

	NumPyArray_Float x(x_); 
	int nx = x.size1();
	if (!x.checktype()) { return NULL; }
	if (!x.checkdim(1)) { return NULL; }
	
	
	//Algorithm
	int i = 0;
	while(x(i)<=0 & i < nx){
		i++;
	}
	if(x(i)<=0){
		i = 0;//default to zero of no positive entry found (for consistency with argmax)
	}

	//Return Max value
	return Py_BuildValue("i",i);
}

/* ===== findClosest =========
find index in b of the closest element in b to a[i]; La = Ly
*/
static PyObject * findClosest(PyObject *self, PyObject *args){
	PyArrayObject *a_,*b_,*y_;

	if (!PyArg_ParseTuple(args, "O!O!O!:findClosest",&PyArray_Type, &a_,
											    &PyArray_Type, &b_,
												&PyArray_Type, &y_
												)){
		return NULL;
	};

	NumPyArray_Float a(a_); 
	if (!a.checktype()) { return NULL; }
	if (!a.checkdim(1)) { return NULL; }
	int na = a.size1();
	
	NumPyArray_Float b(b_); 
	int nb = b.size1();
	if (!b.checktype()) { return NULL; }
	if (!b.checkdim(1)) { return NULL; }

	NumPyArray_Float y(y_); 
	int ny = y.size1();
	if (ny != na) { return NULL; }
	if (!y.checktype()) { return NULL; }
	if (!y.checkdim(1)) { return NULL; }

	//Algorithm 
	int i,j,minIndex;
	double minDiff,thisDiff;
	for(i=0;i<na;i++){
		minDiff = abs(a(i)-b(0));
		minIndex = 0;
		for (j=1;j<nb;j++){
			thisDiff = abs(a(i) - b(j));
			if(thisDiff < minDiff){
				minIndex = j;
				minDiff = thisDiff;
			}
		}
		y(i) = (double) minIndex;
	}

	//Return Max value
	return  Py_BuildValue("i",1);
}


/* ===== firfilter =========
y must be same length as x
first and last (n-1)/2 points of y are invalid

*/
static PyObject * firfilter(PyObject *self, PyObject *args){
	PyArrayObject *x_,*h_,*y_;

	if (!PyArg_ParseTuple(args, "O!O!O!:firfilter",&PyArray_Type, &x_,
											    &PyArray_Type, &h_,
												&PyArray_Type, &y_
												)){
		return NULL;
	};

	NumPyArray_Float x(x_); 
	if (!x.checktype()) { return NULL; }
	if (!x.checkdim(1)) { return NULL; }
	int nx = x.size1();
	
	NumPyArray_Float h(h_); 
	int nh = h.size1();
	if (!h.checktype()) { return NULL; }
	if (!h.checkdim(1)) { return NULL; }

	NumPyArray_Float y(y_); 
	int ny = y.size1();
	if (ny != nx) { return NULL; }
	if (!y.checktype()) { return NULL; }
	if (!y.checkdim(1)) { return NULL; }

	//Algorithm 
	int i,j,it;
	double a;
	int n_1 = nh-1;
	int b = n_1/2;
	for(i = n_1; i < nx;i++){
		it = i - n_1;	
		a = 0;
		for (j=0;j<nh;j++){
			a += h(n_1-j)*x(it+j);
		}
		y(i-b) = a;
	};

	//Return Max value
	return  Py_BuildValue("i",1);
}






/* ===== sunAngle_helper =========
Multiply vector x by scalar float a, return new vector y
*/
static PyObject * sunAngle_helper(PyObject *self, PyObject *args){
	double JD;

	if (!PyArg_ParseTuple(args, "d:sunAngle_helper",&JD)){
		return NULL;
	};

	double PI = 3.141592653589793238462643383;
	double DEG_TO_RAD = PI/180.0;
	double RAD_TO_DEG = 180.0/PI;

	double T, M, L0, DL, L, eps, X, Y, Z, R, delta, RA, theta0;

    //Number of Julian Centuries since 2000/01/01 at 12UT:
    T = (JD - 2451545.0)/36525.0;

    //Solar Coordinates:
    //Mean anomaly:
    M = 357.52910 + 35999.05030*T - .0001559*T*T - 0.00000048*T*T*T ;   //[deg]
    //Mean longitude:
    L0 = 280.46645 + 36000.76983*T + 0.0003032*T*T;   //[deg]
    DL = (1.914600 - 0.004817*T - 0.000014*T*T)*sin(DEG_TO_RAD*M) + (0.019993 - 0.000101*T)*sin(DEG_TO_RAD*2*M) + 0.000290*sin(DEG_TO_RAD*3*M);

    //True longitude:
    L = L0 + DL;    //[deg]

    //Convert ecliptic longitude L to right ascension RA and declination delta:
    eps = 23.43999; //[deg] obliquity of ecliptic
    X = cos(DEG_TO_RAD*L);
    Y = cos(DEG_TO_RAD*eps)*sin(DEG_TO_RAD*L);
    Z = sin(DEG_TO_RAD*eps)*sin(DEG_TO_RAD*L);
    R = sqrt(1.0-Z*Z);

    delta = RAD_TO_DEG*atan2(Z,R);  //[deg] declination -- latitude position of sun --
    RA = 7.63943726841098*atan2(Y,X+R); //[hours] right ascension
    RA = RA*360.0/24.0;  //[deg] right ascension

    //Compute Sidereal time at Greenwich (only depends on time)
    theta0 = 280.46061837 + 360.98564736629*(JD-2451545.0) + 0.000387933*T*T - T*T*T/38710000.0; //[deg]
    theta0 = fmod(theta0,360.0);


	//Return new array y
	return Py_BuildValue("(d,d,d)",theta0,delta,RA);
}



double sinc(double x){
	x *= 3.14159265358979;
	if (fabs(x)<0.0001){
		return 1.0;
	}
	else{
		return sin(x)/x;
	}
}


/* ===== find_harmonics_helper =========
helper function to cfind_harmonics_lsC

*/
static PyObject * find_harmonics_helper(PyObject *self, PyObject *args){
	PyArrayObject *i_m_j_,*i_p_j_,*A_,*B_,*C_;
	double a,N;
	double PI = 3.141592653589793238462643383;

	if (!PyArg_ParseTuple(args, "O!O!O!O!O!dd:find_harmonics_helper",&PyArray_Type, &i_m_j_,
															  &PyArray_Type, &i_p_j_,
															  &PyArray_Type, &A_,
															  &PyArray_Type, &B_,
															  &PyArray_Type, &C_,
															  &a,&N
															  )){
		return NULL;
	};

	NumPyArray_Float i_m_j(i_m_j_); 
	if (!i_m_j.checktype()) { return NULL; }
	if (!i_m_j.checkdim(2)) { return NULL; }
	int n = i_m_j.size1();
	int m = i_m_j.size2();
	
	//No error checking:
	NumPyArray_Float i_p_j(i_p_j_); 
	NumPyArray_Float A(A_); 
	NumPyArray_Float B(B_); 
	NumPyArray_Float C(C_); 





	//Algorithm 
	double a2p, m1, m2, x_i_m_j, x_i_p_j,inv_sinc_i_m_j,inv_sinc_i_p_j, G1, G2, G3, G4;
    a2p = a/2.0/PI;
	m1 = 2*N-1.0;
    m2 = N-1.0;
	int i,j;
	for (i = 0; i < n;i++){
		for (j=0; j<m; j++){
			x_i_m_j = i_m_j(i,j)*a2p;
			x_i_p_j = i_p_j(i,j)*a2p;

			inv_sinc_i_m_j = 1/sinc(x_i_m_j);
			inv_sinc_i_p_j = 1/sinc(x_i_p_j);

			G1 = sinc(m1*x_i_m_j)*inv_sinc_i_m_j;
			G2 = sinc(m1*x_i_p_j)*inv_sinc_i_p_j;
			G3 = sinc(m2*x_i_m_j)*inv_sinc_i_m_j*sin(a*(i_m_j(i,j))*N/2.0);
			G4 = sinc(m2*x_i_p_j)*inv_sinc_i_p_j*sin(a*(i_m_j(i,j))*N/2.0);

			A(i,j) = .25*m1*(G1 + G2) + .5;
			B(i,j) = .25*m1*(G1 - G2);
			C(i,j) = .5*m2*(G3 + G4);
		}
	}

	//Return Max value
	return  Py_BuildValue("i",1);
}



/* ===== mcossin =========
calculates the cosine of a matrix x and the sine of a matrix y of the same size
*/
static PyObject * mcossin(PyObject *self, PyObject *args){
	PyArrayObject *x_,*y_;

	if (!PyArg_ParseTuple(args, "O!O!:mcossin",&PyArray_Type, &x_,
											   &PyArray_Type, &y_)){
		return NULL;
	};

	NumPyArray_Float x(x_);
	NumPyArray_Float y(y_);
	if (!x.checktype()) { return NULL; }
	if (!y.checktype()) { return NULL; }	//no further error checking on y; assume same size as x
	int nd = x.dim();
	if (nd > 3) { return NULL; }
	int i,j,k,n,m,p;
	
	
	if (nd==1){
		n = x.size1();
		for (i=0;i<n;i++){
			x(i) = cos(x(i));
			y(i) = sin(y(i));
		}
	}

	if (nd==2){
		n = x.size1();
		m = x.size2();
		for (i=0;i<n;i++){
			for (j=0;j<m;j++){
				x(i,j) = cos(x(i,j));
				y(i,j) = sin(y(i,j));
			}
		}
	}

	if (nd==3){
		n = x.size1();
		m = x.size2();
		p = x.size3();
		for (i=0;i<n;i++){
			for (j=0;j<m;j++){
				for (k=0;k<p;k++){
					x(i,j,k) = cos(x(i,j,k));
					y(i,j,k) = sin(y(i,j,k));
				}
			}
		}
	}

	//Return Max value
	return Py_BuildValue("i",i);
}


/* ===== isolateHum_helper =========
helper function to removeHum._isolateHum_ls

*/
static PyObject * isolateHum_helper(PyObject *self, PyObject *args){
	PyArrayObject *A_,*phi_,*k_,*t_,*y_;
	double f0;
	double PI = 3.141592653589793238462643383;

	if (!PyArg_ParseTuple(args, "O!O!O!O!O!d:isolateHum_helper",&PyArray_Type, &A_,
															  &PyArray_Type, &phi_,
															  &PyArray_Type, &k_,
															  &PyArray_Type, &t_,
															  &PyArray_Type, &y_,
															  &f0
															  )){
		return NULL;
	};

	//No error checking:
	NumPyArray_Float A(A_);
	NumPyArray_Float phi(phi_); 
	NumPyArray_Float k(k_); 
	int N = A.size1(); //number of harmonics
	
	NumPyArray_Float t(t_);
	NumPyArray_Float y(y_);
	int L = t.size1(); //length of time vector and y

	//Algorithm 
	int i,j;
	double fctr,Ai,phii;
	for (i=0;i<N;i++){
		fctr = 2*PI*f0*k(i);
		Ai = A(i);
		phii = phi(i);
		for(j=0;j<L;j++){
			y(j) +=  Ai*cos(fctr*t(j)+phii);
		}
	}

	//Return Max value
	return  Py_BuildValue("i",1);
}







/* ---------- /
/ Doc Strings /
/------------*/
static char multXbyAI_doc[] = "multXbyAI(x,a)\nmultiply numpy float array x by float a (in-place, returns 1 for success)";
static char multXbyA_doc[] = "y = multXbyAI(x,a)\nmultiply numpy float array x by float a, return y";
static char myMax_doc[] = "(imax,max) = myMax(x)\nReturn the index of and the maximum value of 1-d array x";
static char rowMax_doc[] = "rowMax(x,ind,max)\nReturn the index of and the maximum value of each row in 2-d array x";
static char delta_filt_doc[] = "delta_filt(x,index,win,y,ii_lower,ii+upper)\nDelta filt with f0 encoded in y; y contains result";
static char firstPos_doc[] = "firstPos(x)\nReturns index of first positive value; returns zero if no positive entry found";
static char findClosest_doc[] = "findClosest(a,b,y)\nfind index in b of the closest element in b to a[i]; La = Ly";
static char firfilter_doc[] = "firfilter(x,h,y)\ncomputes x*h, with a zero-adjustment of (n-1)/2";
static char sunAngle_helper_doc[] = "sunAngle_helper(JD)\nHelper to globe.sunAngle in globe.py";
static char find_harmonics_helper_doc[] = "find_harmonics_helper\nHelper to cfind_harmonics_lsC in sig_proc.py";
static char mcossin_doc[] = "mcossin(x,y)\nCalculates the cosine of a 1,2, or 3-dimensional matrix x and the sine of y";
static char isolateHum_helper_doc[] = "isolateHum_helper\nHelper to sig_proc.removeHum.isolateHum_ls";


/* ----------  /
/ Method Table /
/------------ */

static PyMethodDef np_extensions_Methods[] = {
	{"multXbyAI",multXbyAI,METH_VARARGS,multXbyAI_doc},
	{"multXbyA",multXbyA,METH_VARARGS,multXbyA_doc},
	{"myMax",myMax,METH_VARARGS,myMax_doc},
	{"rowMax",rowMax,METH_VARARGS,rowMax_doc},
	{"delta_filt",delta_filt,METH_VARARGS,delta_filt_doc},
	{"firstPos",firstPos,METH_VARARGS,firstPos_doc},
	{"findClosest",findClosest,METH_VARARGS,findClosest_doc},
	{"firfilter",firfilter,METH_VARARGS,firfilter_doc},
	{"sunAngle_helper",sunAngle_helper,METH_VARARGS,sunAngle_helper_doc},
	{"find_harmonics_helper",find_harmonics_helper,METH_VARARGS,find_harmonics_helper_doc},
	{"mcossin",mcossin,METH_VARARGS,mcossin_doc},
	{"isolateHum_helper",isolateHum_helper,METH_VARARGS,isolateHum_helper_doc},
	{NULL,NULL}
};

PyMODINIT_FUNC initnp_extensions(){
	Py_InitModule("np_extensions",np_extensions_Methods);
	import_array();
}