"""Statistics application."""
from pyof.v0x01.controller2switch.stats_request import StatsType

from kytos.core import KytosNApp, log
from kytos.core.helpers import listen_to
from napps.kytos.of_stats import settings
from napps.kytos.of_stats.stats import FlowStats, PortStats


class Main(KytosNApp):
    """Main class for statistics application."""

    def setup(self):
        """Initialize all statistics and set their loop interval."""
        self.execute_as_loop(settings.STATS_INTERVAL)

        # Initialize statistics
        msg_out = self.controller.buffers.msg_out
        app_buffer = self.controller.buffers.app
        self._stats = {StatsType.OFPST_PORT.value: PortStats(msg_out,
                                                             app_buffer),
                       StatsType.OFPST_FLOW.value: FlowStats(msg_out,
                                                             app_buffer)}

    def execute(self):
        """Query all switches sequentially and then sleep before repeating."""
        switches = list(self.controller.switches.values())
        for switch in switches:
            if switch.is_connected():
                self._update_stats(switch)

    def shutdown(self):
        """End of the application."""
        log.debug('Shutting down...')

    def _update_stats(self, switch):
        for stats in self._stats.values():
            if switch.connection is not None:
                stats.request(switch.connection)

    @listen_to('kytos/of_core.v0x01.messages.in.ofpt_stats_reply')
    def listen_v0x01(self, event):
        """Detect the message body type."""
        stats_reply = event.content['message']
        stats_type = stats_reply.body_type
        self._listen(event, stats_type)

    @listen_to('kytos/of_core.v0x04.messages.in.ofpt_multipart_reply')
    def listen_v0x04(self, event):
        """Detect the message body type."""
        multipart_reply = event.content['message']
        stats_type = multipart_reply.multipart_type
        self._listen(event, stats_type)

    def _listen(self, event, stats_type):
        """Listen to all stats reply we deal with.

        Note: v0x01 ``body_type`` and v0x04 ``multipart_type`` have the same
        values.  Besides, both ``msg.body`` have the fields/attributes we use.
        Thus, we can treat them the same way and reuse the code.
        """
        msg = event.content['message']
        if stats_type.value in self._stats:
            stats = self._stats[stats_type.value]
            stats_list = msg.body
            stats.listen(event.source.switch, stats_list)
        else:
            log.debug('No listener for %s = %s in %s.', stats_type.name,
                      stats_type.value, list(self._stats.keys()))
