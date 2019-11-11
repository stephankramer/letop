from firedrake import (Mesh, SpatialCoordinate, FunctionSpace, interpolate,
                        assemble, CellDiameter, File)
from ufl import sin, pi, dx

from parameters_heat_exch import height, width, inlet_width, dist_center, inlet_depth, shift_center, line_sep
from parameters_heat_exch import OUTMOUTH1, OUTMOUTH2, INMOUTH1, INMOUTH2, INLET1, INLET2, OUTLET1, OUTLET2, WALLS

from optimization_problem import OptimizationProblem
from regularization_solver import RegularizationSolver
from steepest_descent import SteepestDescent

import sys
sys.path.append('..')
from lestofire import HJStabSolver, SignedDistanceSolver

mesh = Mesh('./mesh_heat_exchanger.msh')

X = SpatialCoordinate(mesh)
x, y = X[0], X[1]
phi_expr = -y + line_sep \
            + (y > line_sep + 0.2)*(-2.0*sin((y-line_sep - 0.2)*pi/0.5))*sin(x*pi/width) \
            - (y < line_sep)*(0.5*sin((y + line_sep/3.0)*pi/(2.0*line_sep/3.0)))* \
                    sin(x*pi*2.0/width)

PHI = FunctionSpace(mesh, 'CG', 1)
phi = interpolate(phi_expr , PHI)
opti_problem = OptimizationProblem(mesh, phi)

J = opti_problem.cost_function_evaluation(phi)
dJ = opti_problem.derivative_evaluation(phi)
print("Cost function: {0:.5f}".format(J))
import numpy as np
print("Sum for dJ: {0:.5f}".format(np.sum(np.abs(dJ.dat.data))))

## Line search parameters
alpha0_init,ls,ls_max,gamma,gamma2 = [0.5,0,8,0.1,0.1]
alpha0 = alpha0_init
alpha  = alpha0 # Line search step

## Stopping criterion parameters
Nx = 100
ItMax,It,stop = [int(1.5*Nx), 0, False]


from firedrake import (VectorElement, TestFunction, TrialFunction, Function)
S = FunctionSpace(mesh, VectorElement("Lagrange", mesh.ufl_cell(), 1))
velocity = Function(S)
reg_solver = RegularizationSolver(S, mesh, dx=dx)

phi_old = Function(PHI)
hmin = 0.00940 # Hard coded from FEniCS
hj_solver = HJStabSolver(mesh, PHI, c2_param=1.0)
reinit_solver = SignedDistanceSolver(mesh, PHI, dt=1e-6)
parameters = {
    "mat_type" : "aij",
    "ksp_type" : "preonly",
    "ksp_converged_reason" : None,
    "pc_type" : "lu",
    "pc_factor_mat_solver_type" : "mumps"
}

output_dir = "./test_heat_exchanger/"
phi_pvd = File(output_dir + "phi_evo.pvd")
phi_pvd.write(phi)
ItMax = 21
Jarr = np.zeros( ItMax )

opti_solver = SteepestDescent(opti_problem, reg_solver, pvd_output=phi_pvd)

opti_solver.solve(phi, velocity, solver_parameters=parameters)

print("Jarr at 20: {0:.10f}".format(Jarr[20]))
from numpy.testing import assert_allclose
assert_allclose(Jarr[20], -46471.13659, rtol=1e-3, atol=1e-6, err_msg='Optimization broken')

#while It < ItMax and stop == False:
#
#    J = opti_problem.cost_function_evaluation(phi)
#    Jarr[It] = J
#
#    # CFL condition
#    maxv = np.max(phi.vector()[:])
#    dt = 1e0 * alpha * hmin / maxv
#    print("dt: {:.5f}".format(dt))
#    # ------- LINE SEARCH ------------------------------------------
#    if It > 0 and Jarr[It] > Jarr[It-1] and ls < ls_max:
#        ls   += 1
#        alpha *= gamma
#        phi.assign(phi_old)
#        phi.assign(hj_solver.solve(velocity, phi, steps=3, dt=dt))
#        print('Line search iteration : %s' % ls)
#        print('Line search step : %.8f' % alpha)
#        print('Function value        : %.10f' % Jarr[It])
#    else:
#        print('************ ITERATION NUMBER %s' % It)
#        print('Function value        : %.10f' % Jarr[It])
#        #print('Compliance            : %.2f' % )
#        #print('Volume fraction       : %.2f' % (vol/(lx*ly)))
#        # Decrease or increase line search step
#        if ls == ls_max: alpha0 = max(alpha0 * gamma2, 0.1*alpha0_init)
#        if ls == 0:      alpha0 = min(alpha0 / gamma2, 1)
#        # Reset alpha and line search index
#        ls,alpha,It = [0,alpha0, It+1]
#
#        dJ = opti_problem.derivative_evaluation(phi)
#        reg_solver.solve(velocity, dJ, solver_parameters=parameters)
#
#        phi_old.assign(phi)
#        phi.assign(hj_solver.solve(velocity, phi, steps=3, dt=dt, solver_parameters=parameters))
#        phi_pvd.write(phi)
#
#        # Reinit the level set function every five iterations.
#        if np.mod(It,5) == 0:
#            Dx = hmin
#            phi.assign(reinit_solver.solve(phi, Dx))
#        #------------ STOPPING CRITERION ---------------------------
#        if It>20 and max(abs(Jarr[It-5:It]-Jarr[It-1]))<2.0e-8*Jarr[It-1]/Nx**2/10:
#            stop = True
#
