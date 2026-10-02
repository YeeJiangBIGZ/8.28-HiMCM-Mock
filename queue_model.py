"""Deterministic transient M/M/c calculation for piecewise constant arrival/capacity blocks.

Requires NumPy/SciPy. No random sampling, local calibration defaults, or station rankings.
The overflow state records the probability of ever exceeding the represented state range;
it is a numerical error monitor, not customer rejection or a physical queue limit.
"""
from dataclasses import dataclass
import math
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.linalg import expm_multiply


@dataclass(frozen=True)
class Block:
    hours: float
    arrival_rate: float
    ports: int


def _validate(blocks, service_rate, initial):
    if not math.isfinite(service_rate) or service_rate <= 0:
        raise ValueError('service_rate must be finite and positive')
    if not blocks:
        raise ValueError('at least one block is required')
    for b in blocks:
        if not math.isfinite(b.hours) or b.hours <= 0:
            raise ValueError('block duration must be finite and positive')
        if not math.isfinite(b.arrival_rate) or b.arrival_rate < 0:
            raise ValueError('arrival rate must be finite and nonnegative')
        if isinstance(b.ports, bool) or not isinstance(b.ports, int) or b.ports < 0:
            raise ValueError('ports must be a nonnegative integer')
    if initial.ndim != 1 or not len(initial) or not np.all(np.isfinite(initial)):
        raise ValueError('initial distribution must be a finite probability vector')
    if np.any(initial < 0) or not np.isclose(initial.sum(), 1, atol=1e-12, rtol=0):
        raise ValueError('initial probabilities must be nonnegative and sum to one')


def _solve(blocks, mu, initial, ceiling):
    # States 0..ceiling plus an absorbing overflow monitor; last two entries
    # integrate queue length and completion intensity via an augmented generator.
    overflow = ceiling + 1
    wait_index, completion_index = ceiling + 2, ceiling + 3
    size = ceiling + 4
    state = np.zeros(size)
    state[:len(initial)] = initial
    snapshots = []
    for b in blocks:
        rows, cols, vals = [], [], []
        for n in range(ceiling + 1):
            departure = min(n, b.ports) * mu
            rows.append(n); cols.append(n); vals.append(-b.arrival_rate-departure)
            if b.arrival_rate:
                rows.append(n+1); cols.append(n); vals.append(b.arrival_rate)
            if departure:
                rows.append(n-1); cols.append(n); vals.append(departure)
                rows.append(completion_index); cols.append(n); vals.append(departure)
            if n > b.ports:
                rows.append(wait_index); cols.append(n); vals.append(n-b.ports)
        generator = coo_matrix((vals,(rows,cols)),shape=(size,size)).tocsr()
        state = expm_multiply(generator*b.hours, state)
        probs = state[:ceiling+1]
        snapshots.append({
            'waiting_vehicle_hours':float(state[wait_index]),
            'completed_visits':float(state[completion_index]),
            'backlog':float(np.dot(np.maximum(np.arange(ceiling+1)-b.ports,0),probs)),
            'in_service':float(np.dot(np.minimum(np.arange(ceiling+1),b.ports),probs)),
            'overflow_probability':float(state[overflow]),
            'probability_mass':float(state[:overflow+1].sum()),
        })
    return dict(snapshots[-1], blocks=snapshots,
                final_state_probabilities=state[:ceiling+1].tolist(), state_ceiling=ceiling)


def evaluate(blocks, service_rate, *, initial_distribution, tolerance=1e-9,
             initial_ceiling=32, max_ceiling=65536):
    """Integrate consecutive blocks from an explicitly supplied initial distribution.

    Waiting/completions are cumulative; backlog is measured after the last block.
    Double the represented state range until overflow and changes in all reported
    block metrics meet tolerance. A run at the maximum is never silently accepted.
    Rates are visits/hour and hours; service_rate is per occupied port.
    """
    blocks = tuple(blocks)
    initial = np.asarray(initial_distribution,dtype=float)
    _validate(blocks,service_rate,initial)
    if not math.isfinite(tolerance) or tolerance <= 0:
        raise ValueError('tolerance must be finite and positive')
    ceiling = max(initial_ceiling,len(initial)-1,max(b.ports for b in blocks)+8)
    previous = None
    while ceiling <= max_ceiling:
        result = _solve(blocks,service_rate,initial,ceiling)
        if previous is not None:
            errors = [abs(a[k]-b[k])/max(1,abs(a[k]))
                      for a,b in zip(result['blocks'],previous['blocks'])
                      for k in ('waiting_vehicle_hours','completed_visits','backlog','in_service')]
            if result['overflow_probability'] < tolerance and max(errors) < tolerance:
                result['state_refinement_error'] = max(errors)
                result['expected_arrivals'] = sum(b.hours*b.arrival_rate for b in blocks)
                initial_count = float(np.dot(np.arange(len(initial)), initial))
                result['conservation_residual'] = (initial_count+result['expected_arrivals']-
                     result['completed_visits']-result['backlog']-result['in_service'])
                return result
        previous=result
        ceiling*=2
    raise RuntimeError('state range did not converge; increase max_ceiling or inspect demand')
