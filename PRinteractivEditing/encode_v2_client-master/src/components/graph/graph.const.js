import CONST from '../graph_utils/const';

export default {
    COORDS_SEPARATOR: ',',
    FORCE_IDEAL_STRENGTH: -100, // TODO: Expose as configurable,
    FORCE_X: 0.06,
    FORCE_Y: 0.06,
    GRAPH_CONTAINER_ID: 'graph-container-zoomable',
    GRAPH_WRAPPER_ID: 'graph-wrapper',
    KEYWORDS: {
        SAME: 'SAME'
    },
    LINK_CLASS_NAME: 'link',
    NODE_CLASS_NAME: 'node',
    ...CONST
};
