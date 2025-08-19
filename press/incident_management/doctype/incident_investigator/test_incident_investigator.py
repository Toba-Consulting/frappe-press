# Copyright (c) 2025, Frappe and Contributors
# See license.txt


from unittest.mock import Mock, patch

import frappe
from frappe.tests.utils import FrappeTestCase
from prometheus_api_client import PrometheusConnect

from press.incident_management.doctype.incident_investigator.incident_investigator import (
	IncidentInvestigator,
)
from press.press.doctype.incident.incident import Incident
from press.press.doctype.server.test_server import (
	create_test_database_server,
	create_test_proxy_server,
	create_test_server,
)
from press.utils.test import foreground_enqueue_doc


def create_test_incident(server: str = "f1-mumbai.frappe.cloud") -> Incident:
	return frappe.get_doc({"doctype": "Incident", "alertname": "Test Alert", "server": server}).insert()


def get_mock_prometheus_client() -> PrometheusConnect:
	monitor_server = "monitor.frappe.cloud"
	password = frappe.mock("password")
	return PrometheusConnect(f"https://{monitor_server}/prometheus", auth=("frappe", password))


def mock_prometheus_connection(*args, **kwargs):
	return None


def mock_disk_usage(is_high: bool = False, mountpoint: str = "/opt/volumes/benches"):
	def wrapper(*args, **kwargs):
		return [
			{
				"metric": {
					"__name__": "node_filesystem_avail_bytes",
					"cluster": "Mumbai",
					"device": "/dev/nvme1n1p1",
					"fstype": "ext4",
					"instance": "f1-mumbai.frappe.cloud",
					"job": "node",
					"mountpoint": mountpoint,
				},
				"value": [1755018815.605, "383623069" if is_high else "38362306900"],
			}
		]

	return wrapper


def mock_memory_usage(is_high: bool = False):
	def wrapper(*args, **kwargs):
		return [
			{
				"metric": {"cluster": "Mumbai", "instance": "f1-mumbai.frappe.cloud", "job": "node"},
				"values": [
					[1754985451, "95.2898590348854" if is_high else "25.2898590348854"],
					[1754985511, "95.4377568478028" if is_high else "25.4377568478028"],
					[1754985571, "95.52556306561247" if is_high else "25.52556306561247"],
					[1754985631, "95.36888264068959" if is_high else "25.36888264068959"],
					[1754985691, "95.46091957826147" if is_high else "25.46091957826147"],
					[1754985751, "95.56957190519466" if is_high else "25.56957190519466"],
				],
			}
		]

	return wrapper()


def mock_system_load(is_high: bool = False):
	def wrapper(*args, **kwargs):
		return [
			{
				"metric": {
					"__name__": "node_load5",
					"cluster": "Mumbai",
					"instance": "f1-mumbai.frappe.cloud",
					"job": "node",
				},
				"values": [
					[1754985464.335, "13.95" if is_high else "3.95"],
					[1754985524.335, "13.17" if is_high else "3.17"],
					[1754985584.335, "13.8" if is_high else "3.8"],
					[1754985644.335, "13.63" if is_high else "3.63"],
					[1754985704.335, "13.01" if is_high else "3.01"],
				],
			}
		]

	return wrapper


def mock_cpu_usage(is_high: bool = False):
	def wrapper(*args, **kwargs):
		return [
			{
				"metric": {
					"__name__": "node_cpu_seconds_total",
					"cluster": "Mumbai",
					"cpu": "0",
					"instance": "f1-mumbai.frappe.cloud",
					"job": "node",
					"mode": "idle",
				},
				"values": [
					[1754985451, "1191266.01" if is_high else "1191166.01"],
					[1754985751, "1191276.85"],
				],
			},
			{
				"metric": {
					"__name__": "node_cpu_seconds_total",
					"cluster": "Mumbai",
					"cpu": "3",
					"instance": "f1-mumbai.frappe.cloud",
					"job": "node",
					"mode": "idle",
				},
				"values": [[1754985451, "1204578.51"], [1754985751, "1204669.69"]],
			},
		]

	return wrapper()


def make_custom_query_range_side_effect(is_high: bool = False):
	def custom_query_range_side_effect(*args, **kwargs):
		query = args[1] if args else kwargs.get("query")

		if "node_memory_MemAvailable_bytes" in query:
			return mock_memory_usage(is_high=is_high)
		if "node_cpu_seconds_total" in query:
			return mock_cpu_usage(is_high=is_high)

		return []

	return custom_query_range_side_effect


@patch(
	"press.incident_management.doctype.incident_investigator.incident_investigator.get_prometheus_client",
	get_mock_prometheus_client,
)
@patch.object(PrometheusConnect, "__init__", new=mock_prometheus_connection)
@patch.object(Incident, "identify_affected_resource", Mock())
@patch.object(Incident, "identify_problem", Mock())
@patch.object(Incident, "take_grafana_screenshots", Mock())
class TestIncidentInvestigator(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		cls.database_server = create_test_database_server()
		cls.proxy_server = create_test_proxy_server()
		cls.server = create_test_server(
			proxy_server=cls.proxy_server.name, database_server=cls.database_server.name
		)

	@patch.object(IncidentInvestigator, "after_insert", Mock())
	def test_investigation_creation_on_incident_creation(self):
		test_incident = create_test_incident(server=self.server.name)
		investigator: IncidentInvestigator = frappe.get_last_doc("Incident Investigator")
		self.assertEqual(investigator.incident, test_incident.name)

	@patch.object(PrometheusConnect, "get_current_metric_value", mock_disk_usage(is_high=True))
	@patch.object(PrometheusConnect, "custom_query_range", make_custom_query_range_side_effect(is_high=True))
	@patch.object(PrometheusConnect, "get_metric_range_data", mock_system_load(is_high=True))
	@patch(
		"press.incident_management.doctype.incident_investigator.incident_investigator.frappe.enqueue_doc",
		foreground_enqueue_doc,
	)
	@patch.object(
		IncidentInvestigator, "investigate_proxy_server", Mock()
	)  # We don't have any sites this will fail
	def test_all_high_metrics(self):
		"""Since instance is not taken into account while mocking both database and sever will have same likely causes"""
		create_test_incident(self.server.name)
		investigator: IncidentInvestigator = frappe.get_last_doc("Incident Investigator")

		for step in investigator.server_investigation_steps:
			self.assertTrue(step.is_likely_cause)

		self.assertEqual(investigator.status, "Completed")

	@patch.object(PrometheusConnect, "get_current_metric_value", mock_disk_usage(is_high=False))
	@patch.object(PrometheusConnect, "custom_query_range", make_custom_query_range_side_effect(is_high=True))
	@patch.object(PrometheusConnect, "get_metric_range_data", mock_system_load(is_high=False))
	def test_varied_metrics(self):
		"""Since instance is not taken into account while mocking both database and sever will have same likely causes"""
		create_test_incident(self.server.name)
		investigator: IncidentInvestigator = frappe.get_last_doc("Incident Investigator")
		investigator.investigate_server()

		for step in investigator.server_investigation_steps:
			if step.method == "has_high_disk_usage" or step.method == "has_high_system_load":
				self.assertFalse(step.is_likely_cause)
			else:
				self.assertTrue(step.is_likely_cause)

	@patch.object(IncidentInvestigator, "after_insert", Mock())
	def test_investigation_cool_off_period(self):
		test_incident_1 = create_test_incident(server=self.server.name)
		investigator: IncidentInvestigator = frappe.get_last_doc("Incident Investigator")
		self.assertEqual(investigator.incident, test_incident_1.name)

		# Cool off period
		test_incident_2 = create_test_incident(server=self.server.name)
		investigator: IncidentInvestigator = frappe.get_last_doc("Incident Investigator")
		self.assertEqual(investigator.incident, test_incident_1.name)
		self.assertEqual(test_incident_1.server, test_incident_2.server)

		# Ingore investigation on self hosted servers
		self_hosted_server = create_test_server(is_self_hosted=True)
		create_test_incident(self_hosted_server.name)
		investigator: IncidentInvestigator = frappe.get_last_doc("Incident Investigator")
		self.assertEqual(investigator.incident, test_incident_1.name)

	@classmethod
	def tearDownClass(cls):
		frappe.db.delete("Database Server", cls.database_server.name)
		frappe.db.delete("Proxy Server", cls.proxy_server.name)
		frappe.db.delete("Server", cls.server.name)
