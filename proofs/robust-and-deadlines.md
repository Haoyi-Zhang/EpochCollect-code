# Static interval planning and whole-phase setup budgets

These deductions use the model and normal form in the other proof files. They are not claims of a new general robust-optimization principle.

## Fixed-sequence interval minimax

For a fixed legal batch sequence sigma and task vector p, write C_sigma(p,rho) as the sum of induced weighted critical paths plus (K-1)rho. Every term is coordinatewise nondecreasing in p and rho. In a rectangular uncertainty set p in [lower,upper], rho in [0,rhobar], the joint upper corner belongs to the set. Consequently max C_sigma = C_sigma(upper,rhobar). Taking the minimum over all fixed batch sequences proves

    min_sigma max_box C_sigma = min_sigma C_sigma(upper,rhobar).

The event normal-form theorem applied to upper durations shows that the supplied event solver attains this static optimum when its search completes. This does not interchange an adaptive decision with a worst-case realization; all batches are fixed before the realization is observed. Under reliable observed completion, the upper-corner cost is an execution bound, not permission to reconfigure at a nominal timer.

If upper(v) <= alpha p_actual(v) and rhobar <= beta rho_actual for alpha,beta >= 1, compare the chosen static sequence with the actual-duration optimum. Its actual cost is no larger than its upper cost, that upper cost is optimal at the upper corner, and the upper cost of the actual-optimal sequence is at most max(alpha,beta) times its actual cost. Chaining these three inequalities proves the advertised relative bound.

Taskwise nominal dominance does not imply taskwise dominance for every duration realization. Let a use AB for nominal 10, b use BE for 1 after a, and independent d use CD for 10. At zero setup, the original sequence {a},{b,d} costs 20; its nominal horizon-normal replacement {a,d},{b} costs 11. If a actually takes 1, b finishes at 2 in the original sequence but at 11 in the replacement. This refutes the stronger taskwise-robust interpretation while leaving the fixed-batch upper bound intact. Twelve four-task cases enumerate every legal sequence and all duration/setup corners; twenty-four five-task cases compare overestimate plans against a separate actual optimum. The general proof is the monotonicity argument, not the finite count.

## Exact whole-phase deadline inversion

Suppose F is a completed exact nondominated set of (K,B), where K>=1 is epoch count and B>0 total service. A whole-phase deadline T is feasible for a uniform nonnegative setup rho iff some pair satisfies B+(K-1)rho <= T. If every B>T, even rho=0 is infeasible. If some feasible pair has K=1, setup is irrelevant because initial configuration is free; the feasible budget is unbounded. Otherwise each feasible point contributes the interval

    0 <= rho <= (T-B)/(K-1),

so their union ends at the largest of these thresholds. The maximizing point is an attaining witness and every larger setup violates every point. A dominated point cannot enlarge the feasible union because a point with no larger K or B has no larger cost for all rho>=0. Thus using the nondominated frontier loses nothing. These thresholds are exact rational numbers. The query cannot prove that an arbitrary supplied frontier is complete.

For the retained broadcast, selective pairs (4,41),(6,38) and saturated pair (4,43) yield budgets 7/5 and 2/3 at T=45. At T=50, the selective optimum changes to four epochs with budget 3. In the equal-count family, for m>=2 and T>=2m-1+mL, both policies use K=2m-1 and their setup budgets differ by L/2. Between their zero-setup costs only selection is feasible. These are algebraic deductions, not calibrated physical delay budgets.

## Boundaries of count/service labels and maximal matchings

Two independent conflicting tasks of duration 1 and 10 have the same terminal label (2,11) in either order. Their sums of completion times are 12 and 21. Consequently count/service labels suffice for makespan but do not encode arbitrary regular objectives, even though the normal-form theorem ensures that those objectives have a horizon-normal optimum. Additional labels are required for weighted completion or per-task deadlines.

Uniform setup also matters. Use unit tasks a on AB, b on BC after a, and independent d on CD. The only maximal matchings are A={AB,CD}, B={BC}. Assign setup 100 in both directions between A and B, zero to all other transitions, and a free initial configuration. Every maximal-only solution uses A and B and costs at least 102, attained by {a,d} then {b}. The nonmaximal sequence {AB},{BC},{CD} costs 3. Thus nonnegative but topology-dependent setup invalidates maximal-only dominance. The proof used a bound on the number of equal charges, not a triangle inequality or an arbitrary transition-cost comparison.
