# Drained matching epochs: model and proofs

These are mathematical proofs for the model below. The accompanying finite Python checks are not a mechanized proof of the general results. No statement here certifies an optical device, GPU kernel, bounded-buffer transport, or deployed collective library.

## Definitions

Let P be a finite endpoint set, n=|P|>=2, and m=floor(n/2). An instance is a nonempty finite DAG G=(V,E) with N tasks. Task v requires one unordered pair q(v)={a,b}, a!=b, and a positive service duration p(v). Input indices are a topological order. For every pair, add precedence edges between consecutive tasks on that pair in input order. G henceforth means this augmented DAG. These edges implement a fixed, global FIFO order; choosing a different queue order is not part of the optimization.

An ideal I contains all predecessors of every v in I. A schedule is a chain of ideals empty=I_0 < I_1 < ... < I_K=V. Its nonempty batches are S_j=I_j\I_{j-1}. The support Q(S) is the set of distinct pairs used by tasks of S. A support is a matching when distinct pairs are disjoint. Tasks on a pair may repeat, but they are serialized by FIFO edges.

An epoch fixes the matching Q(S) and admits exactly S. Tasks may become ready during the epoch and then execute; readiness does not imply admission of a task outside S. All admitted tasks finish before the epoch ends. Different supported pairs may execute concurrently. There is no forwarding inside a task, no external release, no finite-buffer blocking, no capacity reclamation, and no failure. Storage is reserved in advance. Local computation is absent or already accounted for in the stated positive task durations. The controller starts any admitted task as soon as its predecessors finish. Initially the first matching is available without charge. Each later nonempty epoch incurs a uniform globally blocking setup rho>=0.

For nonempty S, h_p(S) is the maximum sum of vertex weights on a directed path in the induced graph G[S]. A singleton is a path. Induced paths use only vertices of S. The schedule's cost is C=sum_j h_p(S_j)+(K-1)rho. Consecutive epochs with compatible union are permitted in the encoding but can be merged without increasing cost. Thus charging such redundant boundaries does not artificially improve either optimum. In particular, the exact-k spectrum can contain dominated schedules with redundant boundaries; it is not a claim that each boundary changes a physical link.

For ideal I and matching M, define cl_M(I) as follows. Start from I, repeatedly add an uncompleted task whose pair belongs to M and whose predecessors are already in the set, and stop at the fixed point. This is independent of addition order: equivalently process tasks once in the supplied topological order. It is the largest ideal J containing I such that every vertex of J\I uses a pair in M. An epoch with input I and batch S is saturated if cl_Q(S)(I)=I union S. Saturation therefore exhausts all work recursively unlocked on the installed pairs, not merely tasks ready at epoch entry. C_sel and C_sat denote optimum costs in the selective and saturated classes. K_min denotes minimum epoch count, when the common-count result below has established equality.

## Lemma 1: exact admissibility and service

For an ideal I and nonempty set S disjoint from I, S can be completed in one epoch after I if and only if J=I union S is an ideal and Q(S) is a matching. Its minimum service duration is h_p(S).

**Proof.** If the epoch completes S, every predecessor of a task in S was completed either before the epoch or within it. Thus J is an ideal. All task pairs must be present in the epoch's fixed matching, proving compatibility. Conversely suppose both conditions hold. List S topologically. Define relative finish times

f(v)=p(v)+max({f(u): (u,v) in E, u in S} union {0}).

Tasks on the same pair are totally ordered by the FIFO edges, including any intervening same-pair tasks. An intervening task cannot belong to a future epoch because J is an ideal; if it belongs to I, any earlier same-pair task does too. Therefore same-pair tasks in S never overlap under this recurrence. Tasks on distinct supported pairs have disjoint endpoints. All other dependencies within S are respected by construction; dependencies outside S end in I. The execution is consequently feasible and its last finish is h_p(S), by the standard weighted-path recurrence. Every feasible execution must serialize the tasks of each directed path in G[S], so it cannot finish earlier than h_p(S). This proves exactness. □

The same argument permits positive real durations in the mathematical model. The executable artifact deliberately accepts positive integers, bounded per task by 10^12, and represents them with exact Python integers. Rational durations can be scaled to integers only when that scaling preserves these documented input bounds.

## Corollary 1: logical progress and safe drains

Any finite chain of matching-compatible ideal differences terminates under the model and changes topology only with no admitted task in flight. Every valid instance has such a chain, namely singleton tasks in topological order.

**Proof.** Apply Lemma 1 to each batch in sequence. Each weighted path is finite and every setup is finite, so induction over K epochs gives finite completion. All preceding events finish by the declared end of each epoch, which is the only time a setup may start. □

This is not a claim that DAG acyclicity suffices for arbitrary message-passing implementations. Resource waits not in G may create additional cycles. The adversarial witnesses in the tests are invalid proposed partitions, times, or claims; they are not unschedulable valid input DAGs.

## Lemma 2: monotonicity of closure

If I and I' are ideals with I subset I', then cl_M(I) subset cl_M(I').

**Proof.** Induct over the additions used to construct cl_M(I). Its initial elements already belong to I'. Whenever a new v is added, q(v) is in M and every predecessor has already been added. By induction those predecessors lie in cl_M(I'). The fixed-point property then puts v there as well. This proof uses only monotone readiness and the absence of storage/failure side effects. □

## Theorem 1: saturation preserves minimum epoch count

For every instance, the selective and saturated classes have the same minimum number of nonempty epochs.

**Proof.** Take a selective schedule with matching word M_1,...,M_K and completed prefixes I_0,...,I_K. Put J_0=empty and J_j=cl_M_j(J_{j-1}). Inductively assume I_{j-1} subset J_{j-1}. By Lemma 1, every task in I_j\I_{j-1} can be performed using M_j, so I_j subset cl_M_j(I_{j-1}). Lemma 2 gives I_j subset J_j. Hence J_K=V.

If J_j=J_{j-1}, omit that empty epoch. Otherwise its batch has support contained in M_j. Removing unused pairs from M_j does not change its closure: any task newly reachable using an omitted pair would have belonged to J_j\J_{j-1}, contradicting that the pair was unused there. Thus every retained batch is saturated with respect to its own support. Removing an empty epoch preserves the input completed set for the next retained batch. We obtain a saturated schedule with at most K nonempty epochs. A saturated schedule is also selective, so the reverse inequality between the two minima is immediate. □

This is a count result, not a prefix-time domination result. J_j may contain more completed tasks but finish later. A transformation that advances work can lengthen a globally drained epoch.

## Theorem 2: a saturation price bound

Let W=sum_v p(v). Let L_port=max_a sum_{v:a in q(v)} p(v), let L_path=h_p(V), let B=max(W/m,L_port,L_path), and let c=(K_min-1)rho. Then

1 <= C_sat/C_sel <= (W+c)/(B+c) <= m.

**Proof.** The first inequality follows from containment of feasible classes. By Theorem 1, some saturated schedule has K_min epochs. In each batch, h_p(S)<=sum_{v in S}p(v). Because batches partition V, this schedule costs at most W+c; the saturation optimum is no larger.

In any selective execution, at most m tasks can be executing at once. Integrating the number of active tasks over all non-setup time gives total work W, hence total service-epoch time is at least W/m. Tasks incident on any fixed endpoint cannot overlap, so that time is also at least L_port. Every directed path serializes its positive service, so it is at least L_path. Every schedule uses at least K_min epochs and therefore at least c setup time. Consequently C_sel>=B+c. Finally B>=W/m and c>=0 imply (W+c)/(B+c)<=m. □

The workload comparison is standard scheduling reasoning, not itself a novelty claim. The structural equal-count theorem and the tight restricted construction below identify what this particular saturation rule can lose.

## Theorem 3: tightness at the same minimum epoch count

Fix integers m>=1, L>=1, and rho>=0. Use endpoints 0,...,2m-1 and pairs

p_i={2i,2i+1} (0<=i<m), q_i={2i+1,2i+2} (0<=i<m-1).

For each i, create a unit-duration task a_i on p_i and a duration-L task l_i on p_i, with a_i -> l_i. For i<m-1 create a unit task b_i on q_i and dependencies a_i -> b_i -> a_{i+1}. Task order is a_i,l_i,b_i, with b_{m-1} omitted. FIFO adds no new constraints beyond these paths. Then

K_min=2m-1,
C_sel=2m-1+L+(2m-2)rho,
C_sat=2m-1+mL+(2m-2)rho.

The dependency graph is an out-tree with maximum indegree one and maximum outdegree two; the graph of distinct communication pairs is a path of maximum degree two. For fixed m and rho, C_sat/C_sel tends to m as L tends to infinity.

**Proof of the count lower bound.** The trigger chain a_0,b_0,a_1,b_1,...,a_{m-1} has 2m-1 tasks. Consecutive chain tasks use different pairs sharing an endpoint, so they cannot occur in the same matching epoch. Precedence puts their epoch indices in nondecreasing order; the adjacent conflicts make those indices strictly increasing. Hence K>=2m-1 in every schedule.

**Selective lower bound.** The trigger chain followed by l_{m-1} is a directed path of total service 2m-1+L. The preceding count lower bound adds at least (2m-2)rho setups. Thus the displayed selective cost is a lower bound.

**Selective construction.** Execute a_0,b_0,...,a_{m-2},b_{m-2} in singleton epochs. In the final epoch install the matching of all p_i and admit a_{m-1} and all leaves l_0,...,l_{m-1}. Earlier leaves can start at its beginning; the last leaf follows a_{m-1}. That epoch lasts L+1, earlier epochs have total service 2m-2, and there are exactly 2m-1 epochs. The construction attains the selective lower bound.

**Saturated lower bound.** In any saturated schedule, l_i must be completed in the same epoch as a_i. At that epoch's entry l_i is not yet complete, since it depends on a_i. Once a_i completes, l_i is enabled on the same installed pair. Saturation therefore includes it. The head epochs are distinct, as shown by the trigger chain. Each of the m head epochs consequently lasts at least L+1. The m-1 connector tasks occupy distinct epochs between consecutive heads and contribute at least one each. No connector epoch can be the epoch of any other trigger-chain task: the strictly increasing sequence includes every one of those tasks. Additional epochs cannot reduce these mandatory durations or setup count. Therefore C_sat >= m(L+1)+(m-1)+(2m-2)rho.

**Saturated construction.** Admit {a_i,l_i} for each head epoch and {b_i} for each connector epoch. Each pair's supported tasks are then exhausted. These 2m-1 epochs achieve the saturated lower bound. Dividing the formulas and taking L to infinity proves tightness. The path/out-tree statements follow directly from the listed vertices and edges. For m=1 there is one epoch and both costs are L+1, consistent with every statement. □

This is a synthetic gated-traffic construction. It is not an implementation or semantic decomposition of a standard Allreduce. In particular, naming tasks as heads/leaves does not establish any accelerator application.

## Corollary 2: unit-duration tightness

Replace each l_i by an L-task, unit-duration FIFO chain on p_i, the first task depending on a_i. The formulas and K_min of Theorem 3 remain unchanged.

**Proof.** The last head followed by its unit chain gives the same selective path lower bound. All earlier chains can execute concurrently on the disjoint pairs in the final matching, while the final chain waits one unit for a_{m-1}. Saturation recursively includes the entire chain after its head, enforcing the same m separate durations L+1. The dependency graph remains an out-tree and the pair-support graph is unchanged. The number of tasks becomes m(L+1)+(m-1); the result does not hold that N stays fixed while L increases. □

## Proposition 1: exact null classes and a false null

If every unordered pair labels at most one task, every admissible selective batch is saturated, and the two service spectra coincide. If G is a total order, the two optimum costs coincide for every rho, even if their nonminimal-count spectra differ.

**Proof.** In the first case an unadmitted task cannot use any pair in the batch's support, because each such pair already labels its sole task in the batch. Thus closure adds nothing. In the second case no two tasks can overlap; all schedules have service W. Theorem 1 gives the same minimum epoch count, hence the same optimum W+(K_min-1)rho. □

Independence of the original queues is not a sufficient null condition. On five endpoints, take two FIFO tasks of duration ten on pair AB, one duration-ten task on CD, and one duration-ten task on DE, with no inter-pair dependencies. At rho=0, selective admission pairs the first AB task with CD and the second AB task with DE, for cost 20. Saturation executes both AB tasks during the epoch containing AB, while CD and DE cannot share a matching. The best saturated cost is 30, attained by pairing the AB queue with either CD or DE and executing the other separately. Thus even independent queues can exhibit a packing loss. This four-task counterexample is a retained regression test, not an omitted unfavorable finding.

## Theorem 4: exact bounded synthesis

Let F(J,k) be minimum total service of a selective schedule completing exactly ideal J in k nonempty epochs, with F(empty,0)=0 and all other impossible states infinite. Then

F(J,k)=min_{I proper-subset J, I ideal, Q(J\I) matching} [F(I,k-1)+h_p(J\I)].

The saturated version uses the same recurrence restricted to cl_Q(J\I)(I)=J. The optimum at setup rho is min_k [F(V,k)+(k-1)rho].

**Proof.** Remove the final epoch from any admissible schedule to obtain one of the predecessor states and arcs in the recurrence, by Lemma 1. Thus the recurrence's minimum is no larger than the schedule's service. Conversely, append a feasible last batch to a witness for any finite predecessor state. Lemma 1 gives a valid selective schedule; the extra closure predicate gives a saturated schedule when required. Induction on |J| proves equality and reconstructability. Adding the setup term and minimizing over k gives exact makespan. □

There are at most 2^N subset states. Ordered pairs (I,J) with I subset J are bounded by 3^N, by assigning each task to I, J\I, or V\J. Computing/combining polynomial-size per-state and per-arc information gives O(poly(N) 3^N) time and O(N 2^N) dynamic-programming storage. The implementation rejects N>16 for exact search. The mathematical characterization itself does not assert practical scalability. A path/time certificate proves feasibility, not optimizer optimality; optimum results are supported by this recurrence proof, its transparent implementation, and separate finite cross-checks.

## Theorem 5: bounded-duration replay

Fix a valid chain of batches S_1,...,S_K. Let actual task times p' satisfy 0<p'(v)<=bar_p(v), and actual setup times satisfy 0<=rho'_j<=bar_rho_j. If an epoch ends after its admitted tasks actually complete, not at a nominal wall-clock deadline, then

C_actual <= sum_j h_bar_p(S_j)+sum_{j=2}^K bar_rho_j.

In particular if p'<=alpha p and rho'_j<=beta rho, for alpha,beta>=1, then C_actual<=max(alpha,beta) C_nominal.

**Proof.** Ideal/matching validity depends on order and resource labels, not duration. By Lemma 1, service in batch j is h_p'(S_j). Every path's weight is monotone in each p'(v), so h_p'(S_j)<=h_bar_p(S_j). Summing services and setups gives the first statement. Under multiplicative envelopes, path linearity yields h_p'(S_j)<=alpha h_p(S_j), while the setups total at most beta(K-1)rho. Bounding each term by the larger multiplier proves the second statement. □

Without a finite service bound there is no finite completion bound: a one-task input whose execution can take arbitrarily long already refutes one. Without completion-triggered drains, a nominal one-unit epoch with an actual two-unit task can reconfigure with a task in flight. These two countermodels separate progress assumptions from arithmetic duration guarantees.

## Evidence interpretation

The exhaustive campaign compares the complete selective and saturated service spectra on 6,912 labeled small input encodings with a separately written N^N epoch-assignment enumeration. The event interpreter used by that enumeration and by the certificate checker is independent of the planner's weighted-path implementation; it is not an independent human reviewer and is not free from possible shared modeling errors. Weighted generated examples and symbolic reductions/broadcasts exercise the implementation. They do not establish workload prevalence or replace the proofs above. All generated Allreduce cases and all generated pair-exchange cases have zero selective-vs-optimal-saturated cost gain in the recorded campaign; that null result is retained.
