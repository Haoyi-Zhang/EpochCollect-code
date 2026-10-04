# Completion-dominating admission normal form

This result uses the model in `model.md`: an augmented acyclic task graph,
positive nonpreemptive durations, fixed FIFO order on every unordered endpoint
pair, one half-duplex partner per endpoint, reserved storage, and globally
blocking, uniform, nonnegative reconfiguration delay. Every actual resource
conflict must be represented by the model. No task is interrupted at a horizon.

## Timetable definition

For a completed ideal I and a matching M of the global pair graph, define a
relative timetable t(I,M) in topological order. A task in I has time zero. An
uncompleted task v has time infinity when q(v) is outside M or any predecessor
has infinite time. Otherwise its time is p(v) plus the largest predecessor time,
where the maximum of the empty set is zero. Infinity is a mathematical marker,
not a large numerical constant.

For d >= 0, let H(I,M,d) be I together with the uncompleted tasks whose finite
relative finish is at most d. It includes COMPLETE tasks only. A task starting
before d but finishing afterwards is not admitted. This relative-time expansion
need not be idempotent: invoking another horizon after updating I advances time.

## Lemma: feasibility and exact internal timing

H(I,M,d) is an ideal. For any newly included v, each predecessor is either in I
or has relative finish at most t(v)-p(v) < t(v) <= d. Every newly included task
uses M. Its predecessors have the same values in the restricted ASAP timetable
as in the unrestricted timetable, by topological induction. Fixed FIFO already
serializes any two tasks using one pair; distinct pairs of M share no endpoint.
Thus H minus I executes legally and drains by d. If it is nonempty, its exact
service is the largest included relative finish.

Conversely, suppose S is any legal nonempty batch after I, with support in M.
Every predecessor of an admitted task is in I or S. The induced ASAP timetable
for S is identical, on S, to t(I,M): perform induction over admitted tasks. A
predecessor not in S belongs to I and contributes zero. The FIFO constraint is
indispensable because an omitted earlier same-pair task cannot silently compete
with an admitted task. Consequently S is a subset of H(I,M,h(S)).

## Lemma: earlier completed ideals cannot postpone reachable tasks

If I is a subset of J, and M is a subset of M', then every task having finite
relative time in t(I,M) has finite relative time no larger in t(J,M'). Tasks
already in J have zero time. For any other such task, its pair is in M', and all
predecessors have no larger relative times by induction. Its recurrence then
has no larger value. This compares relative timetables, not completion-set size
alone.

## Theorem: taskwise completion dominance, simultaneously for all setup costs

Take any legal selective schedule with batches S_1,...,S_K, installed supports
M_j, completed ideals I_j, and exact services d_j. Starting with J_0 empty,
choose any maximal matching M'_j in the global pair graph containing M_j, and
set J_j = H(J_{j-1},M'_j,d_j). Remove an empty difference.

Inductively I_j is a subset of J_j. Indeed, a task of S_j that is not already in
J_{j-1} has relative finish at most its original finish within epoch j, by the
two lemmas, hence at most d_j and is included. Thus J_K contains every task.
Every nonempty new batch has service at most its associated d_j and there are
at most K of them. All new batches satisfy the one-epoch admissibility lemma.

Fix any setup cost rho >= 0. The new epoch associated with position j begins
no later than the original epoch j: every preceding retained service is no
larger than its corresponding original service, and there are no more setup
charges. If a task originally in S_j was not completed in an earlier new epoch,
its relative finish in the new epoch is no larger than its original relative
finish. If it was completed earlier, it finishes before that new epoch starts,
which is no later than the original epoch's start. Thus EACH task's new absolute
completion time is no larger than its original completion time. The argument
uses no chosen value of rho: the same normalized batches dominate for all
nonnegative rho.

It follows that the nondominated (epoch count, total service) frontier and every
optimal makespan are unchanged when restricting to horizon-complete batches on
maximal installed matchings. Any nondecreasing objective of the task completion
vector, also nondecreasing in epoch count when count is charged separately,
admits an optimum in this normal form. The supplied dynamic program optimizes
makespan only; optimizing other objectives requires corresponding state labels.

### Scope of the preservation statement

Dominated exact-count spectrum entries need not survive. Three unit tasks on
one pair have service 3 at each of counts 1,2,3; the nondominated frontier has
only (1,3). The normal form preserves optimal values, not every schedule, every
exact-count entry, or exact timestamps. It never claims that unbounded saturation
preserves time. Maximum-cardinality matching is not required: inclusion-maximal
is the correct condition.

## Finite event set and exact dynamic program

For fixed I,M, H changes only at a finite positive task-completion event. There
are at most N such events. Continuous horizon choice therefore reduces exactly
to at most N nonempty candidate differences per maximal matching. Evaluate the
relative timetable in O(N+|E|), sort events in O(N log N), and emit their prefixes.
For R reachable ideals and q maximal matchings, the straightforward label-setting
implementation uses O(R q (N+|E|+N log N+N^2)) arithmetic operations, since an arc
can relax at most N count labels. Integer-mask operations and bit complexity
add factors polynomial in N and the input number of bits. Memory is O(RN+qr),
where r is the number of used endpoint pairs; a state's transient arc list has
at most qN destinations. Matching enumeration itself can be exponential and is
not hidden inside a polynomial-time claim.

Transitions add tasks and cannot cycle. Numeric task masks strictly increase
along transitions, so a min-heap over masks gives a topological state order.
At a state, a label with no smaller count and no smaller service is dominated
for all future extensions. The remaining label recurrence is exact by the
normal-form theorem and induction over states. Parent pointers reconstruct a
schedule checked by an independent event interpreter. A search limit raises an
exception and does not certify a partial result as an optimum.

The FIFO queues give the separate bound R <= product_q (length(q)+1): an ideal
chooses a prefix of each queue. This is polynomial in N for fixed r, not an FPT
claim with a parameter-independent exponent. The queue-prefix baseline enumerates
Cartesian products of per-pair prefixes, using the same state-label engine and
maximal matchings. This isolates the horizon reduction from data-structure changes.

## Why unbounded saturation cannot use the same maximality argument

Use six endpoints and four tasks: AB of duration 1; BE of duration 1 after AB;
AF of duration 10 after BE; CD of duration 10 with no predecessor. Saturated
admission on support AB followed by support {BE,AF,CD} has service 1+11=12 in
2 epochs; the port/path lower bound proves optimality. Every maximal installed
matching contains CD. Saturating a first AB matching therefore also drains CD
for 10 time units, after which BE and AF take 11. The best such restricted
saturated schedule costs 21 before setup. A horizon of 1 on {AB,CD}, however,
admits only AB and retains the optimum 12. Thus maximal installed matching is
safe WITH horizon admission, not with mandatory unbounded saturation.

## Aggregate-demand indistinguishability

In the path/out-tree family, remove all inter-pair trigger dependencies but keep
same-pair FIFO and durations. The aggregate pair demands are unchanged: L+1 on
each p_i and 1 on each q_i. For m >= 2, execute all p_i in one epoch and all q_i
in another. The two policies both attain L+2+rho, matching the port-workload and
minimum-count lower bounds. With the trigger dependencies present their optima
are the original 2m-1+L+(2m-2)rho and 2m-1+mL+(2m-2)rho. Aggregate demand alone
therefore cannot determine the price of saturation. This is an information-loss
example, not a performance comparison against a traffic-matrix scheduler.

## Relation to prior techniques

This is a specialized dominance argument, not the invention of active schedules,
longest-path evaluation, Pareto dynamic programming, or weighted matching. The
specific claim is that fixed FIFO and global drains allow arbitrary admitted
subsets to be replaced by one completion threshold per installed matching while
preserving taskwise completion dominance. Fixed-step interval dynamic programming
and aggregate-demand decompositions have different state information. Their
algorithms can inspire a method but do not, as stated, provide this theorem.
The manuscript supplies explicit source-specific comparisons and no absolute
world-first claim.
