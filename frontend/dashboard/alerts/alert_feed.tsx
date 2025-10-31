import { AlertCard } from './alert_card';
export const AlertFeed = ({items}:{items: any[]}) => <div>{items.map(i=> <AlertCard key={i.id} {...i} />)}</div>;
