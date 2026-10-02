"""Independent analytical checks of the article's transient queue equations."""
import math
import unittest
import numpy as np
from queue_model import Block, evaluate


class QueueChecks(unittest.TestCase):
    def test_no_ports_matches_poisson_accumulation(self):
        r=evaluate([Block(3,2,0)],1,initial_distribution=[1.0])
        self.assertAlmostEqual(r['waiting_vehicle_hours'],9,places=8)
        self.assertAlmostEqual(r['backlog'],6,places=8)
        self.assertAlmostEqual(r['completed_visits'],0,places=8)
        self.assertAlmostEqual(r['conservation_residual'],0,places=8)

    def test_one_existing_request_exponential_completion(self):
        r=evaluate([Block(2,0,1)],.5,initial_distribution=[0,1])
        self.assertAlmostEqual(r['completed_visits'],1-math.exp(-1),places=9)
        self.assertAlmostEqual(r['in_service'],math.exp(-1),places=9)
        self.assertAlmostEqual(r['waiting_vehicle_hours'],0,places=9)

    def test_stationary_mmc_agrees_with_erlang_c(self):
        lam,mu,c=1.5,1.0,2
        a=lam/mu;rho=a/c
        p0=1/(sum(a**n/math.factorial(n) for n in range(c))+
               a**c/(math.factorial(c)*(1-rho)))
        initial=np.array([p0*a**n/math.factorial(n) if n<c else
                          p0*a**c/math.factorial(c)*rho**(n-c) for n in range(160)])
        initial/=initial.sum()
        erlang_c=p0*a**c/(math.factorial(c)*(1-rho))
        lq=erlang_c*rho/(1-rho)
        r=evaluate([Block(4,lam,c)],mu,initial_distribution=initial)
        self.assertAlmostEqual(r['waiting_vehicle_hours'],4*lq,places=7)
        self.assertAlmostEqual(r['completed_visits'],4*lam,places=7)

    def test_block_split_does_not_reset_queue(self):
        whole=evaluate([Block(6,3,2)],1,initial_distribution=[1.0])
        split=evaluate([Block(2,3,2),Block(4,3,2)],1,initial_distribution=[1.0])
        for key in ('waiting_vehicle_hours','completed_visits','backlog'):
            self.assertAlmostEqual(whole[key],split[key],places=8)

    def test_peak_then_recovery_carries_backlog(self):
        r=evaluate([Block(4,3,2),Block(12,.25,2)],1,initial_distribution=[1.0])
        peak,end=r['blocks']
        # At most 8 services can finish on average; Q >= N-c gives E[Q] >= 12-8-2.
        self.assertGreaterEqual(peak['backlog'],2)
        self.assertLess(end['backlog'],.1)
        self.assertGreater(end['waiting_vehicle_hours'],peak['waiting_vehicle_hours'])
        self.assertAlmostEqual(r['conservation_residual'],0,places=7)
        self.assertLess(r['overflow_probability'],1e-9)

    def test_more_ports_reduce_waiting(self):
        low=evaluate([Block(4,3,2),Block(8,.25,2)],1,initial_distribution=[1.0])
        high=evaluate([Block(4,3,3),Block(8,.25,3)],1,initial_distribution=[1.0])
        self.assertLess(high['waiting_vehicle_hours'],low['waiting_vehicle_hours'])
        self.assertGreater(high['completed_visits'],low['completed_visits'])

    def test_expansion_releases_queued_requests_to_new_ports(self):
        r=evaluate([Block(2,2,0),Block(3,0,8)],1,initial_distribution=[1.0])
        self.assertAlmostEqual(r['blocks'][0]['backlog'],4,places=8)
        self.assertGreater(r['completed_visits'],3.7)
        self.assertAlmostEqual(r['conservation_residual'],0,places=7)

    def test_invalid_initial_state_rejected(self):
        with self.assertRaises(ValueError):
            evaluate([Block(1,1,1)],1,initial_distribution=[.5])

if __name__=='__main__':unittest.main()
