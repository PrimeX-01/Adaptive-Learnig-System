import { Component } from 'react';

export default class ErrorBoundary extends Component {
  state = { hasError: false, error: null };
  static getDerivedStateFromError(error) { return { hasError: true, error }; }
  render() {
    if (this.state.hasError) return (
      <div className='ml-60 p-8'>
        <div className='bg-red-500/10 border border-red-500/30 rounded-xl p-6'>
          <h2 className='font-bold text-red-400 mb-2'>Something went wrong</h2>
          <p className='text-sm text-red-300'>{this.state.error?.message}</p>
          <button onClick={()=>this.setState({hasError:false})} className='mt-4 text-sm text-red-400 underline'>Try again</button>
        </div>
      </div>
    );
    return this.props.children;
  }
}