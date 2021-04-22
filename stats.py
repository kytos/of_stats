"""Module with Classes to handle statistics."""
import time
from abc import ABCMeta, abstractmethod

import pyof.v0x01.controller2switch.common as v0x01
# pylint: disable=C0411,C0412
from pyof.v0x01.common.phy_port import Port
from pyof.v0x01.controller2switch.common import AggregateStatsRequest
from pyof.v0x01.controller2switch.stats_request import StatsRequest, StatsType
from pyof.v0x04.controller2switch import multipart_request as v0x04
from pyof.v0x04.controller2switch.common import MultipartType
from pyof.v0x04.controller2switch.multipart_request import MultipartRequest

from kytos.core import KytosEvent, log
# v0x01 and v0x04 PortStats are version independent
from napps.kytos.of_core.flow import FlowFactory
from napps.kytos.of_core.flow import PortStats as OFCorePortStats


class Stats(metaclass=ABCMeta):
    """Abstract class for Statistics implementation."""

    def __init__(self, msg_out_buffer, msg_app_buffer):
        """Store a reference to the controller's buffers.

        Args:
            msg_out_buffer: Where to send events.
            msg_app_buffer: Where to send events to other NApps.

        """
        self._buffer = msg_out_buffer
        self._app_buffer = msg_app_buffer

    @abstractmethod
    def request(self, conn):
        """Request statistics."""

    @abstractmethod
    def listen(self, switch, stats):
        """Listen statistic replies."""

    def _send_event(self, req, conn):
        event = KytosEvent(
            name='kytos/of_stats.messages.out.ofpt_stats_request',
            content={'message': req, 'destination': conn})
        self._buffer.put(event)

    @classmethod
    def _save_event_callback(cls, _event, data, error):
        """Execute the callback to handle with kronos event to save data."""
        if error:
            log.error(f'Can\'t save stats in kytos/kronos: {error}')
        log.debug(data)


class PortStats(Stats):
    """Deal with PortStats messages."""

    def request(self, conn):
        """Ask for port stats."""
        request = self._get_versioned_request(conn.protocol.version)
        self._send_event(request, conn)
        log.debug('PortStats request for switch %s sent.', conn.switch.id)

    @staticmethod
    def _get_versioned_request(of_version):
        if of_version == 0x01:
            return StatsRequest(
                body_type=StatsType.OFPST_PORT,
                body=v0x01.PortStatsRequest(Port.OFPP_NONE))  # All ports
        return MultipartRequest(
            multipart_type=MultipartType.OFPMP_PORT_STATS,
            body=v0x04.PortStatsRequest())

    def listen(self, switch, ports_stats):
        """Receive port stats."""
        debug_msg = 'Received port %s stats of switch %s: rx_bytes %s,' \
                    ' tx_bytes %s, rx_dropped %s, tx_dropped %s,' \
                    ' rx_errors %s, tx_errors %s'

        for port_stat in ports_stats:
            self._update_controller_interface(switch, port_stat)

            statistics_to_send = {'rx_bytes': port_stat.rx_bytes.value,
                                  'tx_bytes': port_stat.tx_bytes.value,
                                  'rx_dropped': port_stat.rx_dropped.value,
                                  'tx_dropped': port_stat.tx_dropped.value,
                                  'rx_errors': port_stat.rx_errors.value,
                                  'tx_errors': port_stat.tx_errors.value}

            port_no = port_stat.port_no.value

            namespace = f'kytos.kronos.{switch.id}.port_no.{port_no}'
            content = {'namespace': namespace,
                       'value': statistics_to_send,
                       'callback': self._save_event_callback,
                       'timestamp': time.time()}
            event = KytosEvent(name='kytos.kronos.save', content=content)
            self._app_buffer.put(event)

            log.debug(debug_msg, port_stat.port_no.value, switch.id,
                      port_stat.rx_bytes.value, port_stat.tx_bytes.value,
                      port_stat.rx_dropped.value, port_stat.tx_dropped.value,
                      port_stat.rx_errors.value, port_stat.tx_errors.value)

    @staticmethod
    def _update_controller_interface(switch, port_stats):
        port_no = port_stats.port_no.value
        iface = switch.get_interface_by_port_no(port_no)
        if iface is not None:
            if iface.stats is None:
                iface.stats = OFCorePortStats()
            iface.stats.update(port_stats)


class AggregateStats(Stats):
    """Deal with AggregateStats message."""

    def request(self, conn):
        """Ask for flow stats."""
        body = AggregateStatsRequest()  # Port.OFPP_NONE and All Tables
        req = StatsRequest(body_type=StatsType.OFPST_AGGREGATE, body=body)
        self._send_event(req, conn)
        log.debug('Aggregate Stats request for switch %s sent.',
                  conn.switch.dpid)

    def listen(self, switch, aggregate_stats):
        """Receive flow stats."""
        debug_msg = 'Received aggregate stats from switch {}:' \
                    ' packet_count {}, byte_count {}, flow_count {}'

        for aggregate in aggregate_stats:
            # need to choose the _id to aggregate_stats
            # this class isn't used yet.

            log.debug(debug_msg, switch.id, aggregate.packet_count.value,
                      aggregate.byte_count.value, aggregate.flow_count.value)

            # Save aggregate stats using kytos/kronos
            namespace = f'kytos.kronos.aggregated_stats.{switch.id}'
            stats_to_send = {'aggregate_id': aggregate.id,
                             'packet_count': aggregate.packet_count.value,
                             'byte_count': aggregate.byte_count.value,
                             'flow_count': aggregate.flow_count.value}

            content = {'namespace': namespace,
                       'value': stats_to_send,
                       'callback': self._save_event_callback,
                       'timestamp': time.time()}

            event = KytosEvent(name='kytos.kronos.save', content=content)
            self._app_buffer.put(event)


class FlowStats(Stats):
    """Deal with FlowStats message."""

    def request(self, conn):
        """Ask for flow stats."""
        request = self._get_versioned_request(conn.protocol.version)
        self._send_event(request, conn)
        log.debug('FlowStats request for switch %s sent.', conn.switch.id)

    @staticmethod
    def _get_versioned_request(of_version):
        if of_version == 0x01:
            return StatsRequest(
                body_type=StatsType.OFPST_FLOW,
                body=v0x01.FlowStatsRequest())
        return MultipartRequest(
            multipart_type=MultipartType.OFPMP_FLOW,
            body=v0x04.FlowStatsRequest())

    def listen(self, switch, flows_stats):
        """Receive flow stats."""
        flow_class = FlowFactory.get_class(switch)
        for flow_stat in flows_stats:
            flow = flow_class.from_of_flow_stats(flow_stat, switch)

            # Update controller's flow
            controller_flow = switch.get_flow_by_id(flow.id)
            if controller_flow:
                controller_flow.stats = flow.stats

            # Save packet_count using kytos/kronos
            namespace = f'kytos.kronos.{switch.id}.flow_id.{flow.id}'
            content = {'namespace': namespace,
                       'value': {'packet_count': flow.stats.packet_count},
                       'callback': self._save_event_callback,
                       'timestamp': time.time()}

            event = KytosEvent(name='kytos.kronos.save', content=content)
            self._app_buffer.put(event)

            # Save byte_count using kytos/kronos
            namespace = f'kytos.kronos.{switch.id}.flow_id.{flow.id}'
            content = {'namespace': namespace,
                       'value': {'byte_count': flow.stats.byte_count},
                       'callback': self._save_event_callback,
                       'timestamp': time.time()}

            event = KytosEvent(name='kytos.kronos.save', content=content)
            self._app_buffer.put(event)
